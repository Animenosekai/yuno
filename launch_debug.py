from yuno.launcher import MongoDB, LogConfig
from yuno.client import YunoClient

instance = MongoDB(db_path="test", log_config=LogConfig(path="test.log"), fork=False)

print("Starting Mongo")
instance.start()
print("Mongo started")
client = YunoClient(instance)
print(client)
client.close()
instance.kill()

instance = MongoDB(db_path="test", log_config=LogConfig(path="test.log"), fork=True)

print("Starting Mongo (fork)")
instance.start()
print("Mongo started (fork)")
client = YunoClient(instance)
print(client)
client.close()
instance.kill()