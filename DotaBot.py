import discord
import json
import os
import requests
import random
import time

heroes = {}
with open('heroes.json', 'r') as f:
    heroes = json.load(f)

try:
    # for local
    with open('config.json', 'r') as f:
        config = json.load(f)

    token = config['bottoken']
    api_key = config['ODtoken']

    # for heroku
except FileNotFoundError:
    token = os.environ['bottoken']
    api_key = os.environ['ODtoken']


def loadJsonFile(serverID):
    temp = {}
    try:
        with open('users.json', 'r') as f:
            temp = json.load(f)
    except FileNotFoundError:
        with open('users.json', 'w') as f:
            json.dump({}, f)
    if serverID not in temp.keys():
        temp[serverID] = {}
    users = temp[serverID]
    return users


def writeJsonFile(serverID, users):
    with open('users.json', 'r') as f:
        temp = json.load(f)
    temp[serverID] = users

    # dumping the new values into the file
    with open('users.json', 'w') as f:
        json.dump(temp, f)


class MyClient(discord.Client):

    # TODO: for time rate limiting
    # lim_min = 0
    # lim_mon = 0

    api_url = 'https://api.opendota.com/api'
    key_suffix = f'?api_key={api_key}'

    async def on_ready(self):
        await client.change_presence(activity=discord.Game('!dota to start'))
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    async def on_message(self, message):
        # we do not want the bot to reply to itself
        if message.author.id == self.user.id:
            return

        # basically setting server/user as a global thing
        server = str(message.guild.id)
        users = loadJsonFile(server)

        # setUser command
        if message.content.startswith('!setUser'):
            words = message.content.split(' ')
            users[str(message.author.id)] = words[1]
            writeJsonFile(server, users)
            await message.channel.send(f'{message.author.mention} has their steamID stored as: ' + words[1])

        # printUsers for debug
        elif message.content.startswith('!printUsers'):
            print(users)

        # lastMatch command
        elif message.content.startswith('!lastMatch'):
            if str(message.author.id) not in users:
                await message.channel.send('User not set. Use `!setUser xxxxx` to set your steamID.')
            else:
                steam_id = users[str(message.author.id)]
                # 1 API CALL HERE
                endpoint = f'/players/{steam_id}/recentMatches'
                url = self.api_url + endpoint + self.key_suffix
                response = json.loads(requests.get(url).text)

                p_slot = response[0]['player_slot']
                match_id = response[0]['match_id']

                # general text field
                # TODO: change the hero jawn to a function instead
                duration = int(f"{response[0]['duration']}")
                general = f""" Time: {time.strftime('%m-%d-%Y %H:%M:%S', time.localtime(response[0]['start_time']))}
                               Duration: {int(duration/60)}:{duration%60}, Party Size: {response[0]['party_size']}
                               Hero: {heroes[str(response[0]['hero_id'])]['localized_name']}, {response[0]['kills']}/{response[0]['deaths']}/{response[0]['assists']}"""

                # the message to be sent
                # randomizing the embed color
                c = random.randint(0, 0xFFFFFF)
                embedVar = discord.Embed(title=f"{response[0]['match_id']}", description=general, color=c)

                # 1 API CALL HERE
                endpoint = f'/matches/{match_id}'
                url = self.api_url + endpoint + self.key_suffix
                response = json.loads(requests.get(url).text)

                # match text field
                # if match is won, stomp and comback are available, else throw and loss.
                game = ""

                try:
                    game = f""" Radiant Gold adv: {response['radiant_gold_adv'][-1]}, Radiant XP adv: {response['radiant_xp_adv'][-1]}
                            Stomp: {response['stomp']}, Comeback: {response['comeback']}
                        """
                except KeyError:
                    game = f""" Radiant Gold adv: {response['radiant_gold_adv'][-1]}, Radiant XP adv: {response['radiant_xp_adv'][-1]}
                            Throw (gold): {response['throw']}
                        """

                # adding on the match text as an additional field
                embedVar.add_field(name="Match Information", value=game, inline=False)

                p = -1
                for person in response['players']:
                    if person['player_slot'] == p_slot:
                        p = person

                # player text field
                player = f""" Camps Stacked: {p['camps_stacked']}
                              Hero Dmg: {p['hero_damage']}, Hero Heals: {p['hero_healing']}
                              Max Hero Dmg: {p['max_hero_hit']['value']}
                              From: {p['max_hero_hit']['inflictor']}
                              To: {p['max_hero_hit']['key']}
                              Tower Dmg: {p['tower_damage']}
                              Dmg Taken: {sum(p['damage_taken'].values())}
                              Last Hits: {p['last_hits']}, Denies: {p['denies']}
                              Neutral Kills: {p['neutral_kills']}, Courier Kills: {p['courier_kills']}
                              Net Worth: {p['net_worth']}, GPM: {p['gold_per_min']}, XPM: {p['xp_per_min']}
                              Level: {p['level']}
                              Wards: {p['obs_placed']}, Dewards: {p['observer_kills']}
                              Sentries: {p['sen_placed']}, Desents: {p['sentry_kills']}
                              Runes: {p['rune_pickups']}
                              APM: {p['actions_per_min']}
                              Pings: {p['pings']}"""

                # adding on the player text as an additional field
                embedVar.add_field(name="Match Information", value=player, inline=False)
                await message.channel.send(embed=embedVar)
        # end of !lastMatch command


client = MyClient()
client.run(token)
