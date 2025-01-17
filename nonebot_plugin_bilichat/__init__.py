from nonebot.plugin import PluginMetadata

from .config import __version__, plugin_config, raw_config

cmd_perfix = f"{raw_config.command_start}{plugin_config.bilichat_cmd_start}{raw_config.command_sep}"

__plugin_meta__ = PluginMetadata(
    name="nonebot-plugin-bilichat",
    description="一个通过 OpenAI 来对b站视频进行总结插件",
    usage="直接发送视频链接即可",
    homepage="https://github.com/Aunly/nonebot-plugin-bilichat",
    type="application",
    supported_adapters={"~onebot.v11", "~onebot.v12", "~qqguild", "~mirai2"},
    extra={
        "author": "djkcyl & Well404",
        "version": __version__,
        "priority": 1,
        "menu_data": [
            {
                "func": "添加订阅",
                "trigger_method": "群聊 + 主人",
                "trigger_condition": f"{cmd_perfix}sub",
                "brief_des": "UP 主的昵称或 UID",
            },
            {
                "func": "移除订阅",
                "trigger_method": "群聊 + 主人",
                "trigger_condition": f"{cmd_perfix}unsub",
                "brief_des": "UP 主的昵称或 UID",
            },
            {
                "func": "查看本群订阅",
                "trigger_method": "群聊 + 无限制",
                "trigger_condition": f"{cmd_perfix}check",
                "brief_des": "无",
            },
            {
                "func": "设置是否 at 全体成员，仅 OB11 有效",
                "trigger_method": "群聊 + 主人",
                "trigger_condition": f"{cmd_perfix}atall",
                "brief_des": "UP 主的昵称或 UID，或 `全局`",
            },
            {
                "func": "验证码登录",
                "trigger_method": "无限制 + 主人",
                "trigger_condition": f"{cmd_perfix}smslogin",
                "brief_des": "无",
            },
            {
                "func": "二维码登录",
                "trigger_method": "无限制 + 主人",
                "trigger_condition": f"{cmd_perfix}qrlogin",
                "brief_des": "无",
            },
        ],
    },
)

from . import adapters, commands  # noqa: F401, E402
