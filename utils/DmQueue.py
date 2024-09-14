import asyncio
import aiofiles
import discord
import time
import re
import uuid6
import json
import threading
import random
class MessageQueue():
    def __init__(self, discordbot):
        self.queue = []
        self.paused = False
        self.bot = discordbot
        self.dmstorage_lock = threading.Lock()
        self.dmcurrent_lock = threading.Lock()
        self.initial_populate_queue()


    def add_random_zero_width_spaces(self, message):
        def add_spaces_to_part(part):
            zero_width_spaces = ''.join('\u200B' for _ in range(random.randint(1, 10)))
            parts = list(part)
            random_index = random.randint(0, len(parts))
            parts.insert(random_index, zero_width_spaces)
            return ''.join(parts)

        # Regex to match URLs
        url_regex = r'(https?://\S+)'
        
        # Split the message into parts that are URLs and parts that aren't
        parts = re.split(url_regex, message)
        
        # Add zero-width spaces to the non-URL parts
        parts = [add_spaces_to_part(part) if not re.match(url_regex, part) else part for part in parts]
        
        return ''.join(parts)


    def initial_populate_queue(self):
        with self.dmcurrent_lock:
            try:
                with open('currentdm.json', 'r') as currentdm_file:
                    currentdm_data = json.load(currentdm_file)
                    for mid in currentdm_data:
                        self.queue.append(mid)
            except FileNotFoundError:
                pass

        with self.dmstorage_lock:
            try:
                with open('dmstorage.json', 'r') as dmstorage_file:
                    dmstorage_data = json.load(dmstorage_file)
                    for mid in dmstorage_data:
                        self.queue.append(mid)
            except FileNotFoundError:
                pass
    
    async def send_message(self, mid, delay=25):
        with self.dmcurrent_lock:
            async with aiofiles.open('currentdm.json', 'r') as dmstorager:
                queuehandler = json.loads(await dmstorager.read())
        if not queuehandler or (isinstance(queuehandler, dict) and not queuehandler):
            with self.dmstorage_lock:
                async with aiofiles.open('dmstorage.json', 'r') as dmstorager:
                    queuehandler = json.loads(await dmstorager.read())
            with self.dmcurrent_lock:
                temp = {}
                temp[mid] = queuehandler[mid]
                async with aiofiles.open('currentdm.json', 'w') as dmstoragew:
                    await dmstoragew.write(json.dumps(temp, indent=4))
            temp = queuehandler
            del temp[mid]
            with self.dmstorage_lock:
                async with aiofiles.open('dmstorage.json', 'w') as dmstoragew:
                    await dmstoragew.write(json.dumps(temp, indent=4))
            with self.dmcurrent_lock:
                async with aiofiles.open('currentdm.json', 'r') as dmstorager:
                    queuehandler = json.loads(await dmstorager.read())
        try:
            guild = self.bot.get_guild(queuehandler[mid]["server"])
        except:
            return
        userlist = queuehandler[mid]["members"]
        # Create a separate list for non-bot members
        non_bot_members = []
        for member_id in userlist:
            try:
                if not guild.get_member(member_id).bot:
                    non_bot_members.append(member_id)
            except Exception as e:
                print(e)
                continue

        # Create a copy of the userlist
        userlist_copy = list(non_bot_members)
        for memberid in non_bot_members:
            member = guild.get_member(memberid)
                
            try:
                while self.paused:
                    await asyncio.sleep(1)
                
                await member.send(self.add_random_zero_width_spaces(queuehandler[mid]["message"]))
                await asyncio.sleep(delay)
                userlist_copy.remove(memberid)
                
            except Exception as e:
                print(f"Issue messaging {member} in dm all: {e}")
                userlist_copy.remove(memberid)
                
            queuehandler[mid]["members"] = userlist_copy
                
            # Writing changes back to the file
            with self.dmcurrent_lock:
                async with aiofiles.open('currentdm.json', 'w') as dmstoragew:
                    await dmstoragew.write(json.dumps(queuehandler, indent=4))   
        clean = {}
        with self.dmcurrent_lock:
            async with aiofiles.open('currentdm.json', 'w') as dmstoragew:
                await dmstoragew.write(json.dumps(clean, indent=4))

    def add_message(self, message, serverid, members):
        mid = uuid6.uuid7()
        mid = mid.int
        with self.dmstorage_lock:
            with open('dmstorage.json', 'r') as dmstorager:
                value = json.load(dmstorager)
        value[mid] = {}
        value[mid]["message"] = message
        value[mid]["server"] = serverid
        memberidlist = [member.id for member in members]
        value[mid]["members"] = memberidlist
        with self.dmstorage_lock:
            with open('dmstorage.json', 'w') as dmstorage:
                json.dump(value, dmstorage, indent=4)
        self.queue.append(mid)

    async def process_queue(self):
        while self.queue:
            mid = self.queue.pop(0)
            await self.send_message(str(mid))

    async def pause(self):
        self.paused = True

    async def resume(self):
        self.paused = False

dm_queue_instance = None

def get_dm_queue(bot):
    global dm_queue_instance
    if dm_queue_instance is None:
        dm_queue_instance = MessageQueue(bot)
    return dm_queue_instance
