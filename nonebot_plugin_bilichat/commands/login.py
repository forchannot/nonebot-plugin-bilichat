import json

from bilireq.auth import Auth
from bilireq.login import Login
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State

from ..lib.bilibili_request.auth import bili_grpc_auth, gRPC_Auth, login_from_cache
from .base import bilichat

bili_login_sms = bilichat.command(
    "smslogin",
    permission=SUPERUSER,
)

bili_login_qrcode = bilichat.command(
    "qrlogin",
    permission=SUPERUSER,
)


@bili_login_qrcode.handle()
@bili_login_sms.handle()
async def bili_login_from_cache(matcher: Matcher):
    logger.info("尝试刷新登录")
    if await login_from_cache():
        await matcher.finish(f"账号 uid:{gRPC_Auth.uid} 已登录")
    else:
        await matcher.send("当前登录已失效，尝试重新登陆")


@bili_login_sms.got("username", prompt="请输入B站账号(电话号码)")
async def bili_send_sms(state: T_State, username: str = ArgPlainText()):
    login = Login()
    state["_username_"] = username
    state["_login_"] = login
    try:
        state["_captcha_key_"] = await login.send_sms(username)
    except Exception as e:
        await bili_login_sms.finish(f"无法发送验证码: {e}")


@bili_login_sms.got("sms", prompt="验证码已发送，请在120秒内输入验证码")
async def bili_handle_login(state: T_State, sms: str = ArgPlainText()):
    global gRPC_Auth
    login: Login = state["_login_"]
    try:
        gRPC_Auth = await login.sms_login(code=sms, tel=state["_username_"], cid=86, captcha_key=state["_captcha_key_"])
        logger.debug(gRPC_Auth.data)
        bili_grpc_auth.write_text(json.dumps(gRPC_Auth.data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        await bili_login_sms.finish(f"登录失败: {e}")
    await bili_login_sms.finish("登录成功，已将验证信息缓存至文件")


try:
    from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment

    @bili_login_qrcode.handle()
    async def bili_qrcode_login(event: MessageEvent):
        login = Login()
        qr_url = await login.get_qrcode_url()
        logger.debug(f"qrcode login url: {qr_url}")
        data = "base64://" + await login.get_qrcode(qr_url, base64=True)  # type: ignore
        await bili_login_qrcode.send(MessageSegment.image(data))
        try:
            gRPC_Auth: Auth = await login.qrcode_login(interval=5)  # type: ignore
            logger.debug(gRPC_Auth.data)
            bili_grpc_auth.write_text(json.dumps(gRPC_Auth.data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            await bili_login_sms.finish(f"登录失败: {e}")
        await bili_login_sms.finish("登录成功，已将验证信息缓存至文件")

except Exception:
    pass
