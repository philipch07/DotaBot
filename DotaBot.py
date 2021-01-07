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
    # api_key = config['ODtoken']

    # for heroku
except FileNotFoundError:
    token = os.environ['bottoken']
    # api_key = os.environ['ODtoken']


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


# converts time from epoch/unix time
def convertTime(epoch):
    return f"{time.strftime('%m-%d-%Y %H:%M:%S', time.localtime(epoch))}"


# grabs hero name from heroes.json
def getHero(hero_id):
    return heroes[str(hero_id)]['localized_name']


class MyClient(discord.Client):
    api_url = 'https://api.opendota.com/api'
    # key_suffix = f'?api_key={api_key}'

    async def on_ready(self):
        await client.change_presence(activity=discord.Game('!dota to start'))
        print('Logged in.')

    async def on_message(self, message):
        # we do not want the bot to reply to itself
        if message.author.id == self.user.id:
            return

        # basically setting server/user as a global thing for easier access (PER BOT INSTANCE)
        server = str(message.guild.id)
        users = loadJsonFile(server)

        # help command
        if message.content.startswith('!dota'):
            # randomizing the embed color
            c = random.randint(0, 0xFFFFFF)

            # decription of the commands
            setUser = """Used to set your SteamID. Make sure it matches your Dotabuff/OpenDota ID.
                         Note that it must be set once per server or if the bot restarts."""
            checkUser = "Used to check your SteamID. Make sure it matches your Dotabuff/OpenDota ID."
            lastMatch = "Provides details of your last match."

            # create the embed
            embedVar = discord.Embed(title="Commands:", color=c)
            # Adds the commands
            embedVar.add_field(name="!setUser", value=setUser, inline=False)
            embedVar.add_field(name="!checkUser", value=checkUser, inline=False)
            embedVar.add_field(name="!lastMatch", value=lastMatch, inline=False)

            # sending the embed
            await message.channel.send(embed=embedVar)

        # setUser command
        if message.content.startswith('!setUser'):
            words = message.content.split(' ')
            users[str(message.author.id)] = words[1]
            writeJsonFile(server, users)
            await message.channel.send(f'{message.author.mention} has their steamID now stored as: ' + words[1])

        # checkUser command
        elif message.content.startswith('!checkUser'):
            id = users.get(str(message.author.id))
            await message.channel.send(f'{message.author.mention} currently has their steamID stored as: ' + id)

        # printUsers for debug
        elif message.content.startswith('!printUsers'):
            print(users)

        # lastMatch command
        elif message.content.startswith('!lastMatch'):
            if str(message.author.id) not in users:
                await message.channel.send('User not set. Use `!setUser xxxxx` to set your steamID.')
            else:
                steam_id = users[str(message.author.id)]
                ###################
                # 1 API CALL HERE #
                ###################
                endpoint = f'/players/{steam_id}/recentMatches'
                url = self.api_url + endpoint  # + self.key_suffix
                response = json.loads(requests.get(url).text)

                # if the set steamID doesn't work, p_slot will not be found properly.
                try:
                    p_slot = response[0]['player_slot']
                except KeyError:
                    err_msg = "There was an error trying to find you in your last match. Please use !checkUser to confirm your steamID."
                    await message.channel.send(err_msg)
                    return

                match_id = response[0]['match_id']

                # general text field
                duration = int(f"{response[0]['duration']}")
                dur = f"{int(duration/60)}:{duration%60}"
                general = f""" Time: {convertTime(response[0]['start_time'])} UTC-0
                               Duration: {dur}, Party Size: {response[0]['party_size']}
                               {getHero(response[0]['hero_id'])}, {response[0]['kills']}/{response[0]['deaths']}/{response[0]['assists']}"""

                # the message to be sent
                # randomizing the embed color
                c = random.randint(0, 0xFFFFFF)
                embedVar = discord.Embed(title=f"{response[0]['match_id']}", description=general, color=c)

                # determining win/loss
                wl = False
                rw = bool(response[0]['radiant_win'])
                # determining if the player is radiant/dire
                if 0 <= p_slot <= 127 and rw:
                    wl = True
                elif 0 <= p_slot <= 127 and not rw:
                    wl = False
                elif 128 <= p_slot <= 255 and rw:
                    wl = False
                else:
                    wl = True

                ###################
                # 1 API CALL HERE #
                ###################
                endpoint = f'/matches/{match_id}'
                url = self.api_url + endpoint  # + self.key_suffix
                response = json.loads(requests.get(url).text)

                # match text field
                # change gold/xp advantage according to team
                gold_adv = "Radiant Gold adv: "
                xp_adv = "Radiant XP adv: "

                if response['radiant_gold_adv'][-1] < 0:
                    gold_adv = "Dire Gold adv: "
                if response['radiant_xp_adv'][-1] < 0:
                    xp_adv = "Dire XP adv: "

                # if match is won, stomp and comback are available, else throw and loss.
                game = ""

                # note the trailing spaces are used to avoid people from guessing a win/loss from the size of the spoiler in discord
                # player won and on radiant
                if rw and wl:
                    # if no comeback was made, let the string say N/A
                    if int(response['throw']) == 0:
                        game = f""" {gold_adv} {abs(response['radiant_gold_adv'][-1])}, {xp_adv} {abs(response['radiant_xp_adv'][-1])}
                            Win/Loss: ||Win||
                            ||`Stomp: {response['loss']}, Comeback: N/A            `||
                        """
                    else:
                        game = f""" {gold_adv} {abs(response['radiant_gold_adv'][-1])}, {xp_adv} {abs(response['radiant_xp_adv'][-1])}
                            Win/Loss: ||Win||
                            ||`Stomp: {response['loss']}, Comeback: {response['throw']}            `||
                        """
                # if player lost and on radiant
                elif (not rw) and (not wl):
                    game = f""" {gold_adv} {abs(response['radiant_gold_adv'][-1])}, {xp_adv} {abs(response['radiant_xp_adv'][-1])}
                        Win/Loss: ||Loss||
                        ||`Min enemy gold lead (throw): {response['comeback']}, Max enemy gold lead: {response['stomp']}`||
                    """
                # if player won and on dire
                elif (not rw) and wl:
                    # if no comeback was made, let the string say N/A
                    if int(response['comeback']) == 0:
                        game = f""" {gold_adv} {abs(response['radiant_gold_adv'][-1])}, {xp_adv} {abs(response['radiant_xp_adv'][-1])}
                            Win/Loss: ||Win||
                            ||`Stomp: {response['stomp']}, Comeback: N/A            `||
                        """
                    else:
                        game = f""" {gold_adv} {abs(response['radiant_gold_adv'][-1])}, {xp_adv} {abs(response['radiant_xp_adv'][-1])}
                            Win/Loss: ||Win||
                            ||`Stomp: {response['stomp']}, Comeback: {response['comeback']}            `||
                        """
                # if player lost and on dire
                elif rw and not wl:
                    game = f""" {gold_adv} {abs(response['radiant_gold_adv'][-1])}, {xp_adv} {abs(response['radiant_xp_adv'][-1])}
                        Win/Loss: ||Loss||
                        ||`Min enemy gold lead (throw): {response['throw']}, Max enemy gold lead: {response['loss']}`||
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
                embedVar.add_field(name="Player Information", value=player, inline=False)

                links = f""" https://www.dotabuff.com/matches/{match_id}
                             https://www.opendota.com/matches/{match_id}"""

                embedVar.add_field(name="Links", value=links, inline=False)
                await message.channel.send(embed=embedVar)
        # end of !lastMatch command


client = MyClient()
client.run(token)
