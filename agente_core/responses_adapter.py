"""
ResponsesAdapter — hace que client.chat.completions parezca client.responses.

Permite usar modelos locales (LM Studio, Ollama, etc.) que solo soportan
/v1/chat/completions con el mismo código que usa el agente para OpenAI.

Uso:
    adapter = ResponsesAdapter(openai_client)
    # adapter.responses.create(...)  funciona igual que el cliente real
"""
import json


# ── Objetos de respuesta falsos ────────────────────────────────────────────────

class _TextPart:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class _FakeMessageItem:
    """Simula un item de tipo 'message' del Responses API."""
    def __init__(self, text: str):
        self.type = "message"
        self.role = "assistant"
        self.content = [_TextPart(text)]

    def model_dump(self):
        return {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": p.text} for p in self.content],
        }


class _FakeFunctionCallItem:
    """Simula un item de tipo 'function_call' del Responses API."""
    def __init__(self, name: str, arguments: str, call_id: str):
        self.type = "function_call"
        self.name = name
        self.arguments = arguments
        self.call_id = call_id

    def model_dump(self):
        return {
            "type": "function_call",
            "name": self.name,
            "arguments": self.arguments,
            "call_id": self.call_id,
        }


class _FakeResponse:
    """Simula la respuesta del Responses API a partir de un Choice de chat completions."""
    def __init__(self, choice):
        self.output = []
        msg = choice.message
        if msg.tool_calls:
            for tc in msg.tool_calls:
                self.output.append(_FakeFunctionCallItem(
                    name=tc.function.name,
                    arguments=tc.function.arguments,
                    call_id=tc.id,
                ))
        if msg.content:
            self.output.append(_FakeMessageItem(msg.content))


# ── Adaptador de streaming ─────────────────────────────────────────────────────

class _FakeStreamEvent:
    """Simula el evento response.output_text.delta del Responses API."""
    def __init__(self, delta: str):
        self.type = "response.output_text.delta"
        self.delta = delta


class _StreamContext:
    """Context manager que adapta un stream de chat.completions al formato responses."""

    def __init__(self, client, chat_kwargs: dict):
        self._client = client
        self._chat_kwargs = chat_kwargs
        self._final = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def __iter__(self):
        full_text = ""
        tool_calls_acc: dict[int, dict] = {}

        stream = self._client.chat.completions.create(**self._chat_kwargs, stream=True)
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if delta.content:
                full_text += delta.content
                yield _FakeStreamEvent(delta.content)

            if delta.tool_calls:
                for tc_d in delta.tool_calls:
                    idx = tc_d.index
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                    if tc_d.id:
                        tool_calls_acc[idx]["id"] += tc_d.id
                    if tc_d.function and tc_d.function.name:
                        tool_calls_acc[idx]["name"] += tc_d.function.name
                    if tc_d.function and tc_d.function.arguments:
                        tool_calls_acc[idx]["arguments"] += tc_d.function.arguments

        # Construir respuesta final
        output = []
        for idx in sorted(tool_calls_acc):
            tc = tool_calls_acc[idx]
            output.append(_FakeFunctionCallItem(tc["name"], tc["arguments"], tc["id"]))
        if full_text:
            output.append(_FakeMessageItem(full_text))

        self._final = type("_FinalResponse", (), {"output": output})()

    def get_final_response(self):
        return self._final


# ── Namespace .responses ───────────────────────────────────────────────────────

class _ResponsesNamespace:
    """Expone .create() y .stream() traduciendo a chat.completions internamente."""

    def __init__(self, client):
        self._client = client

    # ── Traductores de formato ─────────────────────────────────────────────────

    @staticmethod
    def _translate_messages(messages: list) -> list:
        """Traduce el array de mensajes del Responses API al formato Chat Completions."""
        result = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            if not isinstance(msg, dict):
                i += 1
                continue

            msg_type = msg.get("type")
            role = msg.get("role")

            # ── Sistema ───────────────────────────────────────────────────────
            if role == "system":
                result.append({"role": "system", "content": msg.get("content", "")})
                i += 1

            # ── Usuario (con soporte de visión) ───────────────────────────────
            elif role == "user":
                content = msg.get("content", "")
                if isinstance(content, list):
                    parts = []
                    for part in content:
                        t = part.get("type", "")
                        if t == "input_text":
                            parts.append({"type": "text", "text": part.get("text", "")})
                        elif t == "input_image":
                            parts.append({
                                "type": "image_url",
                                "image_url": {"url": part.get("image_url", "")},
                            })
                        else:
                            parts.append(part)
                    result.append({"role": "user", "content": parts})
                else:
                    result.append({"role": "user", "content": content})
                i += 1

            # ── Llamada a herramienta (del asistente) ─────────────────────────
            elif msg_type == "function_call":
                # Recoger todas las function_calls consecutivas (puede haber varias)
                tool_calls = []
                j = i
                while j < len(messages) and messages[j].get("type") == "function_call":
                    fc = messages[j]
                    tool_calls.append({
                        "id": fc.get("call_id", f"call_{j}"),
                        "type": "function",
                        "function": {
                            "name": fc.get("name", ""),
                            "arguments": fc.get("arguments", "{}"),
                        },
                    })
                    j += 1
                # Mensaje de texto del asistente que puede acompañar las tool calls
                asst_text = None
                if j < len(messages) and messages[j].get("type") == "message":
                    c = messages[j].get("content", "")
                    asst_text = (
                        " ".join(p.get("text", "") for p in c if isinstance(p, dict))
                        if isinstance(c, list) else str(c)
                    )
                    j += 1
                result.append({
                    "role": "assistant",
                    "content": asst_text,
                    "tool_calls": tool_calls,
                })
                i = j

            # ── Resultado de herramienta ──────────────────────────────────────
            elif msg_type == "function_call_output":
                raw = msg.get("output", "")
                # Desempaquetar el wrapper {"files": ...} que usa process_response
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict) and "files" in parsed:
                        raw = parsed["files"]
                except Exception:
                    pass
                result.append({
                    "role": "tool",
                    "tool_call_id": msg.get("call_id", ""),
                    "content": str(raw),
                })
                i += 1

            # ── Respuesta del asistente (sin herramientas) ────────────────────
            elif msg_type == "message" or role == "assistant":
                content = msg.get("content", "")
                if isinstance(content, list):
                    text = " ".join(
                        p.get("text", "") if isinstance(p, dict) else str(p)
                        for p in content
                    )
                else:
                    text = str(content) if content else ""
                result.append({"role": "assistant", "content": text})
                i += 1

            else:
                i += 1

        return result

    @staticmethod
    def _translate_tools(tools: list) -> list:
        """Traduce el formato de herramientas del Responses API a Chat Completions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "parameters": t.get("parameters", {}),
                },
            }
            for t in tools
        ]

    def _build_chat_kwargs(self, kwargs: dict) -> dict:
        messages = self._translate_messages(kwargs.get("input", []))
        tools = self._translate_tools(kwargs.get("tools", []))
        out = {
            "model": kwargs["model"],
            "messages": messages,
            "max_tokens": kwargs.get("max_output_tokens", 8192),
        }
        if tools:
            out["tools"] = tools
            out["tool_choice"] = "auto"
        return out

    # ── API pública ────────────────────────────────────────────────────────────

    def create(self, **kwargs) -> _FakeResponse:
        chat_kwargs = self._build_chat_kwargs(kwargs)
        resp = self._client.chat.completions.create(**chat_kwargs)
        return _FakeResponse(resp.choices[0])

    def stream(self, **kwargs) -> _StreamContext:
        chat_kwargs = self._build_chat_kwargs(kwargs)
        return _StreamContext(self._client, chat_kwargs)


# ── Clase principal ────────────────────────────────────────────────────────────

class ResponsesAdapter:
    """
    Envuelve un cliente OpenAI y expone .responses.create() / .responses.stream()
    implementados sobre chat.completions.

    Ejemplo:
        raw_client = OpenAI(api_key=..., base_url=...)
        client = ResponsesAdapter(raw_client)
        # Ahora client.responses.create(...) funciona con cualquier modelo local.
    """

    def __init__(self, openai_client):
        self.responses = _ResponsesNamespace(openai_client)
