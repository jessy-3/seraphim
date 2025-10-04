from api.utils import listen_for_commands

if __name__ == "__main__":
    import asyncio

    asyncio.run(listen_for_commands())
