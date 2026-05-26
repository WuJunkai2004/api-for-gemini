from server.utils.config import ConfigManager


def check():
    config = ConfigManager()
    print("config loaded successfully")
    if config is ConfigManager():
        print("config is a singleton")
    print(f"config values: {config}")


if __name__ == "__main__":
    check()
