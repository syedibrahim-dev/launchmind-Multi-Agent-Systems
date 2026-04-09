import uuid
from datetime import datetime, timezone


class MessageBus:
    def __init__(self):
        self._bus = {
            "ceo": [],
            "product": [],
            "engineer": [],
            "marketing": [],
            "qa": [],
        }
        self._all_messages = []

    def send(self, from_agent, to_agent, message_type, payload, parent_message_id=None):
        message = {
            "message_id": str(uuid.uuid4()),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message_type": message_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if parent_message_id:
            message["parent_message_id"] = parent_message_id

        self._bus[to_agent].append(message)
        self._all_messages.append(message)

        print(f"\n[BUS] {from_agent.upper()} -> {to_agent.upper()} | type={message_type} | id={message['message_id'][:8]}")
        return message["message_id"]

    def receive(self, agent_name):
        messages = self._bus[agent_name]
        self._bus[agent_name] = []
        return messages

    def get_full_log(self):
        return self._all_messages

    def print_full_log(self):
        print("\n" + "="*60)
        print("FULL MESSAGE LOG")
        print("="*60)
        for msg in self._all_messages:
            print(f"\n[{msg['timestamp']}]")
            print(f"  FROM: {msg['from_agent']} -> TO: {msg['to_agent']}")
            print(f"  TYPE: {msg['message_type']}")
            print(f"  ID:   {msg['message_id'][:8]}")
            if "parent_message_id" in msg:
                print(f"  PARENT: {msg['parent_message_id'][:8]}")
        print("="*60)


# Global singleton
bus = MessageBus()
