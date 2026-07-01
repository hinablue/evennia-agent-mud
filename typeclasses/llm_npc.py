"""本地修正版 LLM NPC，支援 OpenAI-compatible completions/chat-completions。"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from random import choice

from django.conf import settings
from twisted.internet import defer, protocol, reactor, task
from twisted.internet.defer import CancelledError, inlineCallbacks
from twisted.web.client import Agent, HTTPConnectionPool, _HTTP11ClientFactory
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from zope.interface import implementer

from evennia import logger
from evennia.commands.command import Command

from .characters import Character

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import make_iter

DEFAULT_PROMPT_PREFIX = (
    "你現在正在扮演 {name}，其設定描述是：{desc}，目前位於 {location}。"
    " 請只以繁體中文、短句、符合角色口吻的方式回答。"
    " 不要輸出思考過程，不要解釋規則。"
    " 從現在開始，{name} 與 {character} 的對話正式開始。"
)

DEFAULT_LLM_HOST = "http://host.docker.internal:8000"
DEFAULT_LLM_PATH = "/v1/chat/completions"
DEFAULT_LLM_HEADERS = {"Content-Type": ["application/json"]}
DEFAULT_LLM_REQUEST_BODY = {
    "max_tokens": 256,
    "temperature": 0.8,
    "think": False,
    "chat_template_kwargs": {"enable_thinking": False},
    "options": {"enable_thinking": False},
}
DEFAULT_LLM_API_FORMAT = "chat_completions"  # 竣工 |聊天完成 |遺產


@implementer(IBodyProducer)
class StringProducer:
    def __init__(self, body: str):
        self.body = body.encode("utf-8")
        self.length = len(self.body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return defer.succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass


class SimpleResponseReceiver(protocol.Protocol):
    def __init__(self, status_code, d):
        self.status_code = status_code
        self.buf = b""
        self.d = d

    def dataReceived(self, data):
        self.buf += data

    def connectionLost(self, reason=protocol.connectionDone):
        self.d.callback((self.status_code, self.buf))


class QuietHTTP11ClientFactory(_HTTP11ClientFactory):
    noisy = False


class OpenAICompatibleLLMClient:
    def __init__(
        self, hostname=None, pathname=None, custom_api_key=None, custom_model=None
    ):
        self._conn_pool = HTTPConnectionPool(reactor)
        self._conn_pool._factory = QuietHTTP11ClientFactory
        self.hostname = hostname or getattr(settings, "LLM_HOST", DEFAULT_LLM_HOST)
        self.pathname = pathname or getattr(settings, "LLM_PATH", DEFAULT_LLM_PATH)
        self.headers = getattr(settings, "LLM_HEADERS", DEFAULT_LLM_HEADERS)
        self.request_body = getattr(
            settings, "LLM_REQUEST_BODY", DEFAULT_LLM_REQUEST_BODY
        )
        self.prompt_keyname = getattr(settings, "LLM_PROMPT_KEYNAME", "prompt")
        self.api_format = getattr(settings, "LLM_API_FORMAT", DEFAULT_LLM_API_FORMAT)
        self._custom_api_key = custom_api_key
        self._custom_model = custom_model
        self.agent = Agent(reactor, pool=self._conn_pool)

    def _infer_api_format(self):
        if self.api_format and self.api_format != "auto":
            return self.api_format
        if self.pathname.endswith("/chat/completions"):
            return "chat_completions"
        if self.pathname.endswith("/completions"):
            return "completions"
        return "legacy"

    def _build_messages_from_prompt(self, prompt):
        if isinstance(prompt, list) and prompt and isinstance(prompt[0], dict):
            return prompt
        return [{"role": "user", "content": str(prompt)}]

    def _format_request_body(self, prompt):
        request_body = json.loads(json.dumps(self.request_body))
        fmt = self._infer_api_format()
        if fmt == "chat_completions":
            request_body.pop(self.prompt_keyname, None)
            request_body["messages"] = self._build_messages_from_prompt(prompt)
            if self._custom_model:
                request_body["model"] = self._custom_model
        else:
            if isinstance(prompt, list):
                prompt = "\n".join(
                    msg.get("content", "") for msg in prompt if isinstance(msg, dict)
                )
            else:
                prompt = "\n".join(make_iter(prompt))
            request_body[self.prompt_keyname] = prompt
            if self._custom_model:
                request_body["model"] = self._custom_model
        return request_body

    def _handle_llm_response_body(self, response):
        d = defer.Deferred()
        response.deliverBody(SimpleResponseReceiver(response.code, d))
        return d

    def _handle_llm_error(self, failure):
        failure.trap(Exception)
        return (500, failure.getErrorMessage())

    def _get_response_from_llm_server(self, prompt):
        request_body = self._format_request_body(prompt)
        if settings.DEBUG:
            logger.log_info(f"LLM request body: {request_body}")
        headers = dict(self.headers)
        if self._custom_api_key:
            headers["Authorization"] = [f"Bearer {self._custom_api_key}"]
        d = self.agent.request(
            b"POST",
            bytes(self.hostname + self.pathname, "utf-8"),
            headers=Headers(headers),
            bodyProducer=StringProducer(json.dumps(request_body)),
        )
        d.addCallbacks(self._handle_llm_response_body, self._handle_llm_error)
        return d

    def _strip_thinking(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(
            r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL | re.IGNORECASE
        )
        text = re.sub(
            r"^\s*thinking\s*:\s*.*?(?=\n\n|$)",
            "",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        text = re.sub(r"(?m)^\s*//-\s*lathought-\d+\s*$", "", text)
        text = re.sub(r"(?m)^\s*[|:]{2,}\s*$", "", text)
        return text.strip()

    def _extract_from_reasoning(self, reasoning: str) -> str:
        if not reasoning:
            return ""
        quoted = re.findall(r'"([^"]*[\u4e00-\u9fff][^"]*)"', reasoning)
        if quoted:
            return quoted[-1].strip()
        lines = [line.strip(" -*\t") for line in reasoning.splitlines() if line.strip()]
        for line in reversed(lines):
            if re.search(r"[\u4e00-\u9fff]", line) and "thinking" not in line.lower():
                return line.strip()
        return ""

    def _extract_text(self, payload):
        fmt = self._infer_api_format()
        if fmt == "legacy":
            return self._strip_thinking(payload.get("results", [{}])[0].get("text", ""))

        choice = (payload.get("choices") or [{}])[0]

        if fmt == "chat_completions":
            message = choice.get("message") or {}
            text = message.get("content") or choice.get("text") or ""
            reasoning = (
                choice.get("reasoning_content")
                or message.get("reasoning_content")
                or choice.get("thinking")
                or message.get("thinking")
                or payload.get("reasoning_content")
            )
            if reasoning and isinstance(text, str) and reasoning in text:
                text = text.replace(reasoning, "")
            text = self._strip_thinking(text)
            return text or self._extract_from_reasoning(str(reasoning or ""))

        text = choice.get("text", "")
        reasoning = (
            choice.get("reasoning_content")
            or choice.get("thinking")
            or payload.get("reasoning_content")
        )
        if reasoning and isinstance(text, str) and reasoning in text:
            text = text.replace(reasoning, "")
        text = self._strip_thinking(text)
        return text or self._extract_from_reasoning(str(reasoning or ""))

    @inlineCallbacks
    def get_response(self, prompt):
        status_code, response = yield self._get_response_from_llm_server(prompt)
        if status_code != 200:
            logger.log_err(f"LLM API error (status {status_code}): {response}")
            return ""
        payload = json.loads(response)
        if settings.DEBUG:
            logger.log_info(f"LLM response payload: {payload}")
        return self._extract_text(payload)


class LocalLLMNPC(Character):
    """LLM NPC base with the same local equipment/clothing model as Character."""

    prompt_prefix = None
    response_template = AttributeProperty(
        "$You() $conj(say) (to $You(character)): {response}", autocreate=False
    )
    thinking_timeout = AttributeProperty(2, autocreate=False)
    thinking_messages = AttributeProperty(
        [
            "{name} 像是在斟酌你的話。",
            "{name} 安靜地想了一下。",
            "{name} 稍微停頓了一會兒。",
        ],
        autocreate=False,
    )
    max_chat_memory_size = AttributeProperty(25, autocreate=False)
    chat_memory = AttributeProperty(defaultdict(list))

    @property
    def llm_client(self):
        if not self.ndb.llm_client:
            # 首先檢查每個物件的 LLM 設定
            custom_host = getattr(self.db, "llm_host", None)
            custom_api_key = getattr(self.db, "llm_api_key", None)
            custom_model = getattr(self.db, "llm_model", None)

            client_kwargs = {}
            if custom_host:
                # 從自訂 URL 中提取主機名稱和路徑名
                import urllib.parse

                parsed = urllib.parse.urlparse(custom_host)
                client_kwargs["hostname"] = f"{parsed.scheme}://{parsed.netloc}"
                client_kwargs["pathname"] = parsed.path or DEFAULT_LLM_PATH

            if custom_api_key:
                client_kwargs["custom_api_key"] = custom_api_key

            if custom_model:
                client_kwargs["custom_model"] = custom_model

            if client_kwargs:
                self.ndb.llm_client = OpenAICompatibleLLMClient(**client_kwargs)
            else:
                self.ndb.llm_client = OpenAICompatibleLLMClient()
        return self.ndb.llm_client

    @property
    def llm_prompt_prefix(self):
        return self.attributes.get(
            "prompt_prefix",
            default=getattr(
                settings,
                "LLM_PROMPT_PREFIX",
                self.prompt_prefix or DEFAULT_PROMPT_PREFIX,
            ),
        )

    def _add_to_memory(self, character, who_talked, speech):
        memory = self.chat_memory[character]
        memory.append(f"{who_talked.get_display_name(self)}: {speech}")
        self.chat_memory[character] = memory[-self.max_chat_memory_size :]

    def build_prompt(self, character, speech):
        name = self.get_display_name(character)
        charname = character.get_display_name(self)
        memory = self.chat_memory[character]
        prompt = self.llm_prompt_prefix.format(
            name=name,
            desc=self.db.desc or "某個人",
            location=self.location.key if self.location else "虛空",
            character=charname,
        )
        prompt += "\n" + "\n".join(mem for mem in memory)
        return prompt

    def build_messages(self, character):
        npc_name = self.get_display_name(character)
        char_name = character.get_display_name(self)
        system_prompt = self.llm_prompt_prefix.format(
            name=npc_name,
            desc=self.db.desc or "某個人",
            location=self.location.key if self.location else "虛空",
            character=char_name,
        )
        messages = [{"role": "system", "content": system_prompt}]
        for mem in self.chat_memory[character]:
            if ":" in mem:
                speaker, content = mem.split(":", 1)
                role = "assistant" if speaker.strip() == npc_name else "user"
                messages.append({"role": role, "content": content.strip()})
            else:
                messages.append({"role": "user", "content": mem})
        return messages

    def _strip_leading_speaker_label(self, response, character):
        response = (response or "").strip()
        if not response:
            return ""
        npc_names = {
            self.key,
            self.get_display_name(character),
            self.get_display_name(self),
        }
        for name in sorted({n for n in npc_names if n}, key=len, reverse=True):
            pattern = rf"^\s*{re.escape(name)}\s*[:：]\s*"
            response = re.sub(pattern, "", response, count=1, flags=re.IGNORECASE)
        return response.strip()

    @inlineCallbacks
    def at_talked_to(self, speech, character):
        def _respond(response):
            if thinking_defer and not thinking_defer.called:
                thinking_defer.cancel()
            if response:
                response = self._strip_leading_speaker_label(response, character)
                self._add_to_memory(character, self, response)
            else:
                response = "……抱歉，我剛剛有點分神。你可以再說一次嗎？"
            response_text = self.response_template.format(
                name=self.get_display_name(character), response=response
            )
            if character.location:
                character.location.msg_contents(
                    response_text,
                    mapping={"character": character},
                    from_obj=self,
                )
            else:
                character.msg(
                    f"{self.get_display_name(character)} 對你說：{response_text}"
                )

        def _echo_thinking_message():
            thinking_message = choice(
                make_iter(self.db.thinking_messages or self.thinking_messages)
            )
            if character.location:
                thinking_message = thinking_message.format(name="$You()")
                character.location.msg_contents(thinking_message, from_obj=self)
            else:
                thinking_message = thinking_message.format(
                    name=self.get_display_name(character)
                )
                character.msg(thinking_message)

        def _handle_cancel_error(failure):
            failure.trap(CancelledError)

        thinking_defer = task.deferLater(
            reactor, self.thinking_timeout, _echo_thinking_message
        ).addErrback(_handle_cancel_error)
        self._add_to_memory(character, character, speech)
        prompt_or_messages = (
            self.build_messages(character)
            if self.llm_client._infer_api_format() == "chat_completions"
            else self.build_prompt(character, speech)
        )
        yield self.llm_client.get_response(prompt_or_messages).addCallback(_respond)


class CmdLocalLLMTalk(Command):
    key = "talk"

    def parse(self):
        args = self.args.strip()
        if "=" in args:
            name, *speech = args.split("=", 1)
        else:
            name, *speech = args.split(" ", 1)
        self.target_name = name.strip()
        self.speech = speech[0].strip() if speech else ""

    def func(self):
        if not self.target_name:
            self.caller.msg("你想跟誰說話？")
            return
        location = self.caller.location
        target = self.caller.search(self.target_name)
        if not target:
            return
        if location:
            location.msg_contents(
                f"$You() $conj(say) (to $You(target)): {self.speech}",
                mapping={"target": target},
                from_obj=self.caller,
            )
        if hasattr(target, "at_talked_to"):
            target.at_talked_to(self.speech, self.caller)
        else:
            self.caller.msg(f"{target.key} 看起來並不想跟你說話。")
