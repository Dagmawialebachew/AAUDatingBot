from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from database import db
from handlers_main import get_back_main_keyboard  # if you want to reuse "Main Menu" flow
from bot_config import TYPE_LABELS  # mapping for readable transaction types

router = Router()

# --- Constants ---
HISTORY_PAGE_SIZE = 5
BASE_DAILY_LIKES = 10  # adjust to your actual baseline

# --- Reply Keyboards (persistent menus) ---

def get_shop_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Buy Extra Daily Likes (20🪙)")],
            [KeyboardButton(text="🌟 Unlock Premium Vibe Test (50🪙)")],
            [KeyboardButton(text="📜 My History")],
            [KeyboardButton(text="🔙 Main Menu")],
        ],
        resize_keyboard=True
    )

# Optional: dedicated minimal keyboard while viewing history
def get_history_back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Back to Shop")],
            [KeyboardButton(text="🔙 Main Menu")],
        ],
        resize_keyboard=True
    )

# --- Entry point ---

@router.message(F.text == "🪙 Coins & Shop")
async def coins_shop(message: Message):
    user = await db.get_user(message.from_user.id)
    # Defensive: ensure coins exist
    coins = user.get("coins", 0) if user else 0

    text = (
        f"🪙 Your Coins: {coins}\n\n"
        "💰 Earn Coins:\n"
        "• Daily Login: 10 coins\n"
        "• Refer a Friend: 50 coins\n"
        "• Send Confession: 5 coins\n"
        "• Get a Match: 10 coins\n\n"
        "🛍️ Spend Coins:\n"
        "• Extra Daily Likes: 20 coins\n"
        "• Premium Vibe Test: 50 coins\n\n"
        "Pick an option below."
    )
    await message.answer(text, reply_markup=get_shop_keyboard())

# --- Shop actions via reply keyboard ---
# We keep reply-keyboard UX consistent, but do purchases via inline confirmations for clarity.

@router.message(F.text == "➕ Buy Extra Daily Likes (20🪙)")
async def buy_likes_entry(message: Message):
    user = await db.get_user(message.from_user.id)
    coins = user.get("coins", 0) if user else 0

    text = (
        "➕ <b>Extra Daily Likes</b>\n"
        "Cost: 20🪙\n"
        "Effect: Increases today’s like capacity.\n\n"
        f"Current balance: {coins}🪙\n"
        "Proceed with purchase?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Buy for 20🪙", callback_data="buy_likes")],
        [InlineKeyboardButton(text="🔙 Back to Shop", callback_data="back_to_shop")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.message(F.text == "🌟 Unlock Premium Vibe Test (50🪙)")
async def buy_vibe_entry(message: Message):
    user = await db.get_user(message.from_user.id)
    coins = user.get("coins", 0) if user else 0
    premium_unlocked = bool(user.get("premium_vibe_unlocked"))

    if premium_unlocked:
        await message.answer(
            "🌟 Premium Vibe Test is already unlocked.\nYou can access it from your matches.",
            reply_markup=get_shop_keyboard()
        )
        return

    text = (
        "🌟 <b>Premium Vibe Test</b>\n"
        "Cost: 50🪙\n"
        "Effect: Unlocks deeper compatibility insights & richer reports.\n\n"
        f"Current balance: {coins}🪙\n"
        "Proceed with purchase?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Buy for 50🪙", callback_data="buy_vibe")],
        [InlineKeyboardButton(text="🔙 Back to Shop", callback_data="back_to_shop")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.message(F.text == "📜 My History")
async def show_coin_history_message(message: Message):
    text, keyboard = await render_coin_history(message.from_user.id, page=0)
    # Show inline pagination + give a simple reply keyboard to return
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await message.answer("Use buttons below to navigate.", reply_markup=get_history_back_keyboard())

@router.message(F.text == "🔙 Back to Shop")
async def back_to_shop_message(message: Message):
    await coins_shop(message)

@router.message(F.text == "🔙 Main Menu")
async def back_to_main_message(message: Message):
    # If you have a main menu function, use it; otherwise reuse a keyboard
    await message.answer("Back to main menu.", reply_markup=get_back_main_keyboard())

# --- Inline callbacks: purchases + nav ---

@router.callback_query(F.data == "back_to_shop")
async def back_to_shop_callback(callback: CallbackQuery):
    # Cleanly return to the shop entry
    await callback.message.answer("🪙 Coins & Shop", reply_markup=get_shop_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("buy_"))
async def handle_purchase(callback: CallbackQuery):
    user_id = callback.from_user.id
    choice = callback.data

    prices = {"buy_likes": 20, "buy_vibe": 50}
    item_names = {"buy_likes": "Extra Daily Likes", "buy_vibe": "Premium Vibe Test"}

    price = prices.get(choice)
    if price is None:
        await callback.answer("Unknown item.", show_alert=True)
        return

    # Prevent double-unlock for premium vibe
    if choice == "buy_vibe":
        user = await db.get_user(user_id)
        if user and user.get("premium_vibe_unlocked"):
            await callback.answer("Already unlocked.", show_alert=True)
            return

    # Spend coins first
    success = await db.spend_coins(user_id, price, "purchase", f"Purchased {item_names[choice]}")
    if not success:
        await callback.answer("Not enough coins 💀", show_alert=True)
        return

    # Apply benefit
    benefit_text = ""
    if choice == "buy_likes":
        # Increment daily_likes_bonus safely
        await db.increment_field(user_id, "daily_likes_bonus", 1)
        benefit_text = "You gained +1 extra daily like for today!"
    elif choice == "buy_vibe":
        await db.update_user(user_id, {"premium_vibe_unlocked": True})
        benefit_text = "Premium Vibe Test unlocked! Access deeper compatibility in matches."

    await callback.message.answer(
        f"✅ You purchased <b>{item_names[choice]}</b> for {price}🪙!\n\n{benefit_text}",
        parse_mode="HTML",
        reply_markup=get_shop_keyboard()
    )
    await callback.answer()

# --- History: rendering + pagination via inline buttons ---

async def render_coin_history(user_id: int, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
    history = await db.get_transactions(
        user_id,
        offset=page * HISTORY_PAGE_SIZE,
        limit=HISTORY_PAGE_SIZE + 1
    )

    if not history:
        text = "📭 <b>No history yet!</b>\nMake moves to earn or spend coins."
        return text, InlineKeyboardMarkup(inline_keyboard=[])

    text = "📜 <b>Your Coin History</b>\n\n"
    for row in history[:HISTORY_PAGE_SIZE]:
        sign = "➕" if row["amount"] > 0 else "➖"
        label = TYPE_LABELS.get(row["type"], row["type"].replace("_", " ").title())
        # Prefer compact timestamp; you can format if needed
        created = row.get("created_at", "")
        text += (
            f"{sign}{abs(row['amount'])} 🪙 — {label}\n"
            f"<i>{row['description']}</i>\n"
            f"<span class='tg-spoiler'>{created}</span>\n\n"
        )

    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"coin_history_{page - 1}"))
    if len(history) > HISTORY_PAGE_SIZE:
        buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"coin_history_{page + 1}"))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons] if buttons else [])
    return text, keyboard

@router.callback_query(F.data.startswith("coin_history_"))
async def show_coin_history_callback(callback: CallbackQuery):
    try:
        page = int(callback.data.split("_")[2])
    except Exception:
        await callback.answer("Invalid page.", show_alert=True)
        return

    text, keyboard = await render_coin_history(callback.from_user.id, page=page)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        # Fallback: if message is not editable (older, or different type), send new
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()

# --- Helper: enforce daily like limit elsewhere ---
# Example usage in your like action (pseudo):
# allowed_likes_today = BASE_DAILY_LIKES + user.get("daily_likes_bonus", 0)
# current_likes_today = await db.count_today_likes(user_id)
# if current_likes_today >= allowed_likes_today:
#     return await message.answer("You’ve reached today’s like limit. Buy extra likes in the shop.")
