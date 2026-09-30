import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import helpers  # noqa: F401  (sys.path sozlaydi)

import db
import texts
from economy import DIAMOND_PACKAGES, STARS_PACKAGES, STARS_PER_DIAMOND
from handlers import shop, stars


class PackagesTest(unittest.TestCase):
    def test_same_packages_as_card(self):
        self.assertEqual([d for d, _ in STARS_PACKAGES], [d for d, _ in DIAMOND_PACKAGES])

    def test_base_price_and_discounts(self):
        self.assertEqual(dict(STARS_PACKAGES)[1], STARS_PER_DIAMOND)
        per_diamond = [s / d for d, s in STARS_PACKAGES]
        self.assertEqual(per_diamond, sorted(per_diamond, reverse=True))  # katta paket arzonroq
        # Chegirmalar so'mdagi paketlar bilan bir xil.
        som = dict(DIAMOND_PACKAGES)
        for diamonds, price in STARS_PACKAGES:
            self.assertAlmostEqual(price, som[diamonds] / 990 * STARS_PER_DIAMOND, delta=0.5)
        totals = [s for _, s in STARS_PACKAGES]
        self.assertEqual(totals, sorted(totals))  # lekin jami narx doim ko'proq
        self.assertTrue(all(1 <= s <= 10000 for s in totals))


class ValidationTest(unittest.TestCase):
    def test_valid(self):
        payload = stars.build_payload(10, 42)
        self.assertEqual(stars.validate_payment(payload, "XTR", 50, 42), (10, 50))

    def test_invalid(self):
        payload = stars.build_payload(10, 42)
        self.assertIsNone(stars.validate_payment(payload, "XTR", 49, 42))  # narx mos emas
        self.assertIsNone(stars.validate_payment(payload, "USD", 50, 42))  # valyuta
        self.assertIsNone(stars.validate_payment(payload, "XTR", 50, 43))  # boshqa to'lovchi
        self.assertIsNone(stars.validate_payment("stars:7:42", "XTR", 35, 42))  # bunday paket yo'q
        self.assertIsNone(stars.validate_payment("garbage", "XTR", 5, 42))


class PreCheckoutTest(unittest.IsolatedAsyncioTestCase):
    async def test_answers(self):
        q = MagicMock(invoice_payload=stars.build_payload(1, 7), currency="XTR", total_amount=5, answer=AsyncMock())
        q.from_user.id = 7
        await stars.on_pre_checkout(q)
        q.answer.assert_awaited_once_with(ok=True)
        q.total_amount = 1
        q.answer.reset_mock()
        await stars.on_pre_checkout(q)
        self.assertFalse(q.answer.await_args.kwargs["ok"])


class ShopViewTest(unittest.TestCase):
    def test_stars_first_card_toggle(self):
        with patch.object(shop, "CARD_PAYMENTS_ENABLED", True), patch.object(shop, "PAYMENT_CARD_NUMBER", "8600"):
            _, kb = shop.shop_view()
            data = [b.callback_data for row in kb.inline_keyboard for b in row]
            self.assertTrue(data[0].startswith("stars:buy:"))
            self.assertTrue(any(d.startswith("shop:buy:") for d in data))
        with patch.object(shop, "CARD_PAYMENTS_ENABLED", False), patch.object(shop, "PAYMENT_CARD_NUMBER", "8600"):
            _, kb = shop.shop_view()
            data = [b.callback_data for row in kb.inline_keyboard for b in row]
            self.assertFalse(any(d.startswith("shop:buy:") for d in data))


def payment_message(user_id, diamonds, charge_id, stars_amount=None):
    m = MagicMock()
    m.from_user.id = user_id
    m.from_user.full_name = "Ali"
    m.from_user.username = None
    m.answer = AsyncMock()
    p = m.successful_payment
    p.telegram_payment_charge_id = charge_id
    p.invoice_payload = stars.build_payload(diamonds, user_id)
    p.currency = "XTR"
    p.total_amount = stars_amount if stars_amount is not None else dict(STARS_PACKAGES)[diamonds]
    return m


class PaymentFlowTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = patch.object(db, "DB_PATH", os.path.join(self.tmp.name, "t.db"))
        self.p.start()
        await db.init_db()
        self.bot = MagicMock(send_message=AsyncMock(), refund_star_payment=AsyncMock())

    async def asyncTearDown(self):
        await db.close_db()
        self.p.stop()
        self.tmp.cleanup()

    async def diamonds(self, uid):
        return (await db.get_user(uid))["diamonds"]

    async def test_payment_credited_once(self):
        m = payment_message(1, 10, "ch_1")
        await stars.on_successful_payment(m, self.bot)
        await stars.on_successful_payment(m, self.bot)  # Telegram update'ni qayta yubordi
        self.assertEqual(await self.diamonds(1), 10)
        self.assertEqual(m.answer.await_count, 1)
        row = await db.get_star_payment("ch_1")
        self.assertEqual((row["user_id"], row["diamonds"], row["stars"], row["status"]), (1, 10, 50, "paid"))

    async def test_bad_payment_not_credited(self):
        m = payment_message(1, 10, "ch_bad", stars_amount=1)
        with patch.object(stars, "ADMIN_IDS", {99}):
            await stars.on_successful_payment(m, self.bot)
        self.assertIsNone(await db.get_star_payment("ch_bad"))
        self.bot.send_message.assert_awaited()  # adminga xabar

    async def test_refund(self):
        await stars.on_successful_payment(payment_message(1, 10, "ch_2"), self.bot)
        result = await stars.refund_payment(self.bot, "ch_2", force=False)
        self.assertIn("50⭐", result)
        self.bot.refund_star_payment.assert_awaited_once_with(user_id=1, telegram_payment_charge_id="ch_2")
        self.assertEqual(await self.diamonds(1), 0)
        self.assertEqual((await db.get_star_payment("ch_2"))["status"], "refunded")
        # Ikkinchi marta qaytarib bo'lmaydi
        self.assertNotIn("50⭐", await stars.refund_payment(self.bot, "ch_2", force=False))
        self.assertEqual(self.bot.refund_star_payment.await_count, 1)

    async def test_refund_needs_force_when_spent(self):
        await stars.on_successful_payment(payment_message(1, 10, "ch_3"), self.bot)
        await db.spend_balance(1, "diamonds", 7)
        self.assertIn("force", await stars.refund_payment(self.bot, "ch_3", force=False))
        self.bot.refund_star_payment.assert_not_awaited()
        self.assertEqual((await db.get_star_payment("ch_3"))["status"], "paid")
        await stars.refund_payment(self.bot, "ch_3", force=True)
        self.assertEqual(await self.diamonds(1), 0)
        self.assertEqual((await db.get_star_payment("ch_3"))["status"], "refunded")

    async def test_refund_api_error_rolls_back(self):
        from aiogram.exceptions import TelegramBadRequest

        await stars.on_successful_payment(payment_message(1, 10, "ch_4"), self.bot)
        self.bot.refund_star_payment = AsyncMock(side_effect=TelegramBadRequest(MagicMock(), "CHARGE_ALREADY_REFUNDED"))
        result = await stars.refund_payment(self.bot, "ch_4", force=False)
        self.assertIn("❌", result)
        self.assertEqual(await self.diamonds(1), 10)
        self.assertEqual((await db.get_star_payment("ch_4"))["status"], "paid")

    async def test_external_refund_takes_diamonds(self):
        await stars.on_successful_payment(payment_message(1, 10, "ch_5"), self.bot)
        m = MagicMock()
        m.refunded_payment.telegram_payment_charge_id = "ch_5"
        await stars.on_refunded_payment(m, self.bot)
        await stars.on_refunded_payment(m, self.bot)  # takroriy update
        self.assertEqual(await self.diamonds(1), 0)
        self.assertEqual((await db.get_star_payment("ch_5"))["status"], "refunded")

    async def test_paysupport_lists_payments(self):
        await stars.on_successful_payment(payment_message(1, 5, "ch_6"), self.bot)
        m = MagicMock(answer=AsyncMock())
        m.from_user.id = 1
        await stars.cmd_paysupport(m)
        self.assertIn("ch_6", m.answer.await_args.args[0])

    async def test_refund_admin_only(self):
        m = MagicMock(answer=AsyncMock())
        m.from_user.id = 5
        with patch.object(stars, "ADMIN_IDS", set()):
            await stars.cmd_refund(m, self.bot, MagicMock(args="ch_x"))
        m.answer.assert_not_awaited()


class TermsTest(unittest.TestCase):
    def test_required_texts(self):
        self.assertIn("/paysupport", texts.SHOP_FOOTER)
        self.assertLessEqual(len(texts.TERMS_TEXT), 4096)


class CardPackagesTest(unittest.TestCase):
    def test_bigger_package_never_more_expensive_per_diamond(self):
        per_diamond = [price / d for d, price in DIAMOND_PACKAGES]
        self.assertEqual(per_diamond, sorted(per_diamond, reverse=True))


if __name__ == "__main__":
    unittest.main()
