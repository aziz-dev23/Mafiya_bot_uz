"""🤝 Guruh egalariga ulush: o'yinchining Stars xaridi u oxirgi o'ynagan guruhga bog'lanadi va guruh
egasiga xariddagi olmosning OWNER_SHARE_PERCENT foizi yig'iladi. Ulush kasr qismi bilan (milli-olmosda)
yig'iladi va butun 1💎 bo'lganda hisobga tushadi — kichik paketlarni aylantirib foyda olib bo'lmaydi."""
import db

MILLI = 1000


async def revert(owner_id: int, millis: int) -> None:
    """Pul qaytarilganda ulush qaytarib olinadi: yig'indidan ayiriladi (hisobga tushgan bo'lsa —
    kelgusi ulushdan ushlab qolinadi, yig'indi manfiy bo'lishi mumkin)."""
    await db.add_owner_share(owner_id, -millis)
