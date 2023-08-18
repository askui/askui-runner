from askui_runner.config import Config

with open("config-schema.json", "w", encoding="utf-8") as write_stream:
    write_stream.write(Config.schema_json())