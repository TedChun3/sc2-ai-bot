import argparse
import asyncio

import aiohttp

import sc2
from sc2.client import Client
from sc2.protocol import ConnectionAlreadyClosedError


def run_ladder_game(bot):
    parser = argparse.ArgumentParser()
    parser.add_argument("--GamePort", type=int, nargs="?")
    parser.add_argument("--StartPort", type=int, nargs="?")
    parser.add_argument("--LadderServer", type=str, nargs="?")
    parser.add_argument("--OpponentId", type=str, nargs="?")
    parser.add_argument("--RealTime", action="store_true")
    args, _unknown = parser.parse_known_args()

    host = "127.0.0.1" if args.LadderServer is None else args.LadderServer
    host_port = args.GamePort
    lan_port = args.StartPort
    bot.ai.opponent_id = args.OpponentId

    if lan_port is None:
        portconfig = None
    else:
        ports = [lan_port + offset for offset in range(1, 6)]
        portconfig = sc2.portconfig.Portconfig()
        portconfig.server = [ports[1], ports[2]]
        portconfig.players = [[ports[3], ports[4]]]

    game = join_ladder_game(
        host=host,
        port=host_port,
        players=[bot],
        realtime=args.RealTime,
        portconfig=portconfig,
    )
    result = asyncio.run(game)
    return result, args.OpponentId


async def join_ladder_game(
    host,
    port,
    players,
    realtime,
    portconfig,
    save_replay_as=None,
    game_time_limit=None,
):
    ws_url = f"ws://{host}:{port}/sc2api"
    session = aiohttp.ClientSession()
    ws_connection = await session.ws_connect(ws_url, timeout=120)
    client = Client(ws_connection)

    try:
        result = await sc2.main._play_game(
            players[0],
            client,
            realtime,
            portconfig,
            game_time_limit,
        )
        if save_replay_as is not None:
            await client.save_replay(save_replay_as)
    except ConnectionAlreadyClosedError:
        return None
    finally:
        await ws_connection.close()
        await session.close()

    return result
