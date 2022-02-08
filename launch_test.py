from saki.launcher import MongoDB, LogConfig
from saki.client import SakiClient

instance = MongoDB(db_path="test", log_config=LogConfig(path="test.log"), fork=False)

print("Starting Mongo")
instance.start()
print("Mongo started")
client = SakiClient(instance)
print(client)
client.close()
instance.kill()

instance = MongoDB(db_path="test", log_config=LogConfig(path="test.log"), fork=True)

print("Starting Mongo (fork)")
instance.start()
print("Mongo started (fork)")
client = SakiClient(instance)
print(client)
client.close()
instance.kill()