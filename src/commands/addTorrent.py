import requests
from time import time, sleep

from src.objs import *
from src.functions.bars import progressBar
from src.functions.convert import convertSize, convertTime
from src.functions.exceptions import exceptions, noAccount

#: Add torrent into the user's account
def addTorrent(message, userLanguage):
    userId = message.from_user.id
    ac = dbSql.getDefaultAc(userId)

    #! If user has an account
    if ac:
        #! Add torrent in the account
        sent = bot.send_message(message.chat.id, language['collectingInfo'][userLanguage])
        account = Seedr(cookie=ac['cookie'])
        response = account.addTorrent(message.text).json()
        
        #! If torrent added successfully
        if 'user_torrent_id' in response:
            startTime = time()
            bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=f"⬇️ <b>{response['title']}</b>")
            
            torrentId = response['user_torrent_id']
            queue = account.listContents().json()

            #!? Getting the progressUrl from active torrents list
            progressUrl = None
            if queue['torrents']:
                for torrent in queue['torrents']:
                    if torrentId == torrent['id']:
                        progressUrl = torrent['progress_url']

            #! If progressUrl is found
            if progressUrl:
                bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=f"⬇️ <b>{response['title']}</b>\n\n{language['collectingSeeds'][userLanguage]}")
                progressPercentage = 0
                oldText = ''
                
                ## [Alert] Must change this algorithm
                #! Collecting seeds
                for i in range(2, 60):
                    progressResponse = json.loads(requests.get(progressUrl).text[2:-1])
                    
                    #! Break if seeds are collected
                    if 'title' in progressResponse:
                        break
                    
                    #! Increase the amount of sleep in each iteration
                    sleep(i)
                    
                #! If seeds collected successfully
                if 'title' in progressResponse:
                    downloadComplete = False

                    ## [Alert] Must change this algorithm
                    #! Updating download status
                    for _ in range(500):
                        progressPercentage =  progressResponse['progress']
                        text = f"<b>⬇️ {progressResponse['title']}</b>\n\n"
                        
                        #! If download finished
                        if progressResponse['progress'] == 101:
                            text = f"<b>📁 {progressResponse['title']}</b>\n\n"
                            
                            bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=f"{text}{language['copyingToFolder'][userLanguage]}")
                            
                            copyFlag = False
                            ## [Alert] Must change this algorithm
                            for _ in range(2,60):
                                progress = requests.get(progressUrl).text[2:-1]
                                progress = json.loads(progress)

                                if 'folder_created' in progress:
                                    text += f"{language['files'][userLanguage]} /getFiles_{progress['folder_created']}\n{language['link'][userLanguage]} /getLink_{progress['folder_created']}\n{language['delete'][userLanguage]} /delete_{progress['folder_created']}\n\n"
                                    text += language['downloadFinishedIn'][userLanguage].format(convertTime(time() - startTime))
                                    
                                    bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=text)
                                    
                                    downloadComplete = True
                                    copyFlag = True
                                    
                                    break
                                else:
                                    sleep(5)
                            
                            if not copyFlag:
                                bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=language['delayWhileCopying'][userLanguage])
                            
                            break
                        
                        #!? If downloading, update the status
                        else:
                            text += f"{language['size'][userLanguage]} {convertSize(progressResponse['size'])}\n{language['torrentQuality'][userLanguage]} {progressResponse['torrent_quality']}\n{language['seeders'][userLanguage]} {progressResponse['stats']['seeders']}\n{language['leechers'][userLanguage]} {progressResponse['stats']['leechers']}\n{language['downloadingFrom'][userLanguage]} {progressResponse['stats']['downloading_from']}\n{language['uploadingTo'][userLanguage]} {progressResponse['stats']['uploading_to']}\n\n"
                            text += f"{convertSize(progressResponse['download_rate'])}/sec \n{progressBar(progressPercentage)}"
                        
                            #! Show warnings
                            if progressResponse['warnings'] != '[]':
                                warnings = progressResponse['warnings'].strip('[]').replace('"','').split(',')
                                for warning in warnings:
                                    text += f"\n⚠️ {warning.capitalize()}"
                            
                            text += f"\n\n{language['cancel'][userLanguage]} /cancel_{torrentId}\n\n"
                            
                            #! Only edit the text if the response changes
                            if oldText != text:
                                bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=text)
                                oldText = text
                            
                            sleep(3)
                            progressResponse = json.loads(requests.get(progressUrl).text[2:-1])
                    
                    #! If download is taking long time
                    if not downloadComplete:
                        bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=language['delayWhileDownloading'][userLanguage])
                            
                #! If seeds collecting is taking long time
                else:
                    bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=language['delayWhileCollectingSeeds'][userLanguage])
            
            #! If failed to find progressUrl
            else:
                exceptions(message, response, userLanguage)

        #! If no enough space
        elif response['result'] == 'not_enough_space_added_to_wishlist':
            bot.send_message(chat_id=message.chat.id, text=language['noSpace'][userLanguage])

        #! Invalid magnet link
        elif response['result'] == 'parsing_error':
            bot.send_message(chat_id=message.chat.id, text=language['invalidMagnet'][userLanguage])
        
        #! If parallel downloads exceeds
        elif response['result'] == 'queue_full_added_to_wishlist':
            bot.send_message(chat_id=message.chat.id, text=language['parallelDownloadExceed'][userLanguage])
        
        else:
            exceptions(message, response, userLanguage)
        
    #! If no accounts
    else:
        noAccount(message, userLanguage)