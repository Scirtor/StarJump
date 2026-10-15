import asyncio
import pygame  # Explicit import lets Pygbag preload the WebAssembly wheel.
from starjump.app import main

if __name__ == '__main__':
    asyncio.run(main())
