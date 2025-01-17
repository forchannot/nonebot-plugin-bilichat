import re
import shlex
from itertools import chain
from typing import TYPE_CHECKING, Optional, Union, cast

from nonebot import get_bots
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    Message,
    MessageEvent,
    MessageSegment,
    PrivateMessageEvent,
)
from nonebot.exception import FinishedException
from nonebot.log import logger
from nonebot.plugin import on_message
from nonebot.rule import Rule
from nonebot.typing import T_State

from ..config import plugin_config
from ..content import Column, Dynamic, Video
from ..lib.b23_extract import b23_extract
from ..model.arguments import Options, parser
from ..model.exception import AbortError
from ..optional import capture_exception
from .base import get_content_info_from_state, get_futuer_fuctions

if TYPE_CHECKING:
    from ..subscribe.manager import User


async def push(user: "User", text: str = "", url: str = "", image: Optional[bytes] = None, **data):
    ms_image = MessageSegment.image(file=image) if image else ""
    message = Message(text + ms_image + url)
    if user.at_all:
        message = MessageSegment.at("all") + message

    bots = get_bots().values()
    for bot in bots:
        if isinstance(bot, Bot):
            groups = await bot.get_group_list()
            for group in groups:
                if int(user.user_id) == group["group_id"]:
                    try:
                        await bot.send_group_msg(group_id=int(user.user_id), message=message)
                        return
                    except Exception as e:
                        logger.exception(e)


async def get_user_id(event: MessageEvent):
    if isinstance(event, GroupMessageEvent):
        return event.group_id
    return None


async def _bili_check(bot: Bot, event: MessageEvent, state: T_State):
    # 检查并提取 raw_bililink
    if plugin_config.bilichat_enable_self and str(event.get_user_id()) == str(bot.self_id) and event.reply:
        # 是自身消息的情况下，检查是否是回复，是的话则取被回复的消息
        _msgs = event.reply.message
    else:
        # 其余情况取该条消息
        _msgs = event.get_message()

    for _msg in _msgs:
        # 如果是图片格式则忽略
        if _msg.type in ("image", "record", "video"):
            continue
        # b23 格式的链接
        _msg_str = str(_msg)
        if "b23" in _msg_str:
            if b23 := re.search(r"b23.(tv|wtf)[\\/]+(\w+)", _msg_str):  # type: ignore
                state["_bililink_"] = await b23_extract(list(b23.groups()))
                return True
        # av bv cv 格式和动态的链接
        for seg in ("av", "bv", "cv", "dynamic", "opus", "t.bilibili.com"):
            if seg in _msg_str.lower():
                state["_bililink_"] = _msg_str
                return True
    return False


async def _permission_check(bot: Bot, event: MessageEvent, state: T_State):
    # 自身消息
    if str(event.get_user_id()) == str(bot.self_id):
        if plugin_config.bilichat_only_self or plugin_config.bilichat_enable_self:
            state["_uid_"] = event.group_id if isinstance(event, GroupMessageEvent) else event.user_id
            return True
        elif not plugin_config.bilichat_enable_self:
            return False
    elif plugin_config.bilichat_only_self:
        return False
    # 是否 to me
    if plugin_config.bilichat_only_to_me and not event.is_tome():
        return False
    # 私聊消息
    if isinstance(event, PrivateMessageEvent):
        state["_uid_"] = event.get_user_id()
        return plugin_config.verify_permission(event.get_user_id())
    # 群聊消息
    elif isinstance(event, GroupMessageEvent):
        state["_uid_"] = event.group_id
        return plugin_config.verify_permission(event.group_id)
    return False


bilichat = on_message(
    block=plugin_config.bilichat_block,
    priority=1,
    rule=Rule(_permission_check, _bili_check),
)


@bilichat.handle()
def set_options(state: T_State, event: MessageEvent):
    state["_options_"] = parser.parse_known_args(
        list(
            chain.from_iterable(
                shlex.split(str(seg)) if cast(MessageSegment, seg).is_text() else (seg,) for seg in event.get_message()
            )
        ),  # type: ignore
        namespace=Options(),
    )[0]


@bilichat.handle()
async def content_info(event: MessageEvent, state: T_State):
    messag_id = event.message_id
    try:
        content: Union[Column, Video, Dynamic] = await get_content_info_from_state(state)
    except AbortError as e:
        logger.info(e)
        raise FinishedException
    if plugin_config.bilichat_basic_info:
        content_image = await content.get_image(plugin_config.bilichat_basic_info_style)

        msgs = Message(MessageSegment.reply(event.message_id))
        if content_image:
            msgs.append(MessageSegment.image(content_image))
        msgs.append(content.url)
        id_ = await bilichat.send(msgs)
        messag_id = id_["message_id"] if plugin_config.bilichat_reply_to_basic_info else messag_id

    try:
        msgs = Message(MessageSegment.reply(messag_id))
        for msg in await get_futuer_fuctions(content):
            if msg:
                if isinstance(msg, str):
                    msgs.append(msg)
                elif isinstance(msg, bytes):
                    msgs.append(MessageSegment.image(msg))
        if len(msgs) > 1:
            await bilichat.finish(msgs)
    except FinishedException:
        raise
    except AbortError as e:
        if plugin_config.bilichat_show_error_msg:
            await bilichat.finish(MessageSegment.reply(messag_id) + str(e))
    except Exception as e:
        capture_exception()
        logger.exception(e)
        if plugin_config.bilichat_show_error_msg:
            await bilichat.finish(MessageSegment.reply(messag_id) + str(e))
