import cv2
import numpy as np
import random
import time
import pygame  
import threading

# ランダムにターゲット位置を生成
def get_random_target_position(frame_shape):
    height, width, _ = frame_shape
    x = random.randint(50, width - 50)
    y = random.randint(50, height - 50)
    return (x, y)

# アラート音を再生する関数

sound_dict = {}
def play_alert_sound(soundname):
    # もし音がまだロードされていなければロード
    if soundname not in sound_dict:
        sound_dict[soundname] = pygame.mixer.Sound(soundname)
    def play_sound():
        sound_dict[soundname].play() 
    threading.Thread(target=play_sound, daemon=True).start()
    
def change_volume(soundname, volume):
    if soundname in sound_dict:
        sound_dict[soundname].set_volume(volume)
        
def stop_alert_sound(soundname):
    if soundname in sound_dict:
        # スレッドで音を停止
        def stop_sound():
            sound_dict[soundname].stop()
        
        threading.Thread(target=stop_sound, daemon=True).start()

# pygameの初期化
pygame.mixer.init()

# ArUcoマーカーの辞書の設定
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
parameters = cv2.aruco.DetectorParameters()

# 対象のID（0〜8）
seek_ids = [0]

# それぞれのIDに名前をつける
marker_names = {0:'key'}
# marker_names = {4:'as',5:'bs',6:'cd'}
# 待機状態を管理するフラグ
waiting_for_start = True

# カメラの初期化
cap = cv2.VideoCapture(1)

# スコアと制限時間の設定
score = 0
time_duration = 15  # 制限時間（秒）
clear_score = 3  # クリアスコア
#alert変数は後で設定
detected_ids = set()  # seek内で現在のフレームで検出されたIDを追跡
previous_ids = set()  # seek内で前のフレームで検出されたIDを追跡

# ターゲット位置の生成
target_position = get_random_target_position(cap.read()[1].shape)
previous_marker_positions = {}


# スコア状態を管理するフラグ
alert_start =False
alert_active = [0]


while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray= cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

    # 待機状態での表示
    if waiting_for_start:
        k = cv2.waitKey(1)
        if k == ord('q'):
            break
        elif k == ord('s'):
            corners0, ids0, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
            if ids0 is not None:
                print(f'検出ID:{ids0}')
                for i in range(len(ids0)):
                    if ids0[i][0] not in seek_ids:
                        marker_names[ids0[i][0]] = input(f'ID:{ids0[i][0]}の名前:')
                        seek_ids.append(ids0[i][0])
            # if ids is not None:
            #     print(f'検出ID:{ids}')
            #     for i in range(len(ids)):
            #         if ids[i][0] not in seek_ids:
            #             marker_names[ids[i][0]] = input(f'ID:{ids0[i][0]}の名前:')
            #             seek_ids.append(ids[i][0])
            else:
                print('There is no marker')
                
        elif k == ord('g'):# seek_idsがからの時うまくいかない
            if not len(seek_ids) == 0 :
                # print(id_names)
                # アラート状態を管理するフラグ
                alert_active = [0]* len(seek_ids) #0 で通常　1で警告　2で泥棒　-1でクリア
                target_active = -1 #1でなし　1であり　0でクリアか泥棒
                waiting_for_start = False
            else:
                print('There is no marker registered')
                register_str = f's:register,g:startID:{seek_ids}'
        cv2.putText(frame, 's:register,g:start', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, f'ID,Names={marker_names}', (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.imshow('Marker Catch', frame)
    # if waiting_for_start:
    #     cv2.putText(frame, "Please press s to start system", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
    else:
        # if not 'alert_active' in locals():#alert未設定の時
        #     alert_active = [0]* len(seek_ids) #0 で通常　1で警告　2で泥棒　-1でクリア
        #     target_active = -1 #1でなし　1であり　0でクリアか泥棒
        corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
        detected_ids.clear()  # 現在のフレームで検出されたIDをクリア

        if ids is not None:
            for i in range(len(ids)):
                marker_id = ids[i][0]
                if marker_id in seek_ids:
                    detected_ids.add(marker_id)  # 検出されたIDをセットに追加
                    corner = corners[i][0]
                    x = int((corner[0][0] + corner[2][0]) / 2)
                    y = int((corner[0][1] + corner[2][1]) / 2)
                    cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

                    # マーカー名を表示
                    if marker_id in marker_names:
                        label = marker_names[marker_id]
                        cv2.putText(frame, label, (x + 10, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)

                    if marker_id in previous_marker_positions:
                        prev_x, prev_y = previous_marker_positions[marker_id]
                        movement_distance = np.sqrt((x - prev_x) ** 2 + (y - prev_y) ** 2)

                        if movement_distance > 10 and score < clear_score:
                            alert_active[seek_ids.index(marker_id)] = 1
                            if not alert_start:
                                start_time = time.time()
                                alert_start = True
                    previous_marker_positions[marker_id] = (x, y)

                    distance = np.sqrt((x - target_position[0]) ** 2 + (y - target_position[1]) ** 2)
                    if distance < 30 and (2 not in alert_active):#失敗時にスコアが増えないように
                        score += 1
                        stop_alert_sound('alert_sound.mp3')
                        play_alert_sound('getpoint.mp3')
                        cv2.waitKey(100)
                        play_alert_sound('alert_sound.mp3')
                        change_volume('alert_sound.mp3', 1-0.8 * score / clear_score)
                        target_position = get_random_target_position(frame.shape)
                        target_active = -1
                        if score >= clear_score:
                            alert_active = [-1] * len(alert_active)
                            target_active = 0
                            waiting_for_start = True  # スコア達成後に再度待機状態に戻す
                            score = 0  # スコアリセット
                            previous_marker_positions = {}
                            alert_start = False
                            stop_alert_sound('alert_sound.mp3')
                            cv2.waitKey(100)
                            play_alert_sound('clear.mp3')
                            print("Goal score reached! System waiting...")
        if 1 in alert_active:
            play_alert_sound('alert_sound.mp3')
            change_volume('alert_sound.mp3', 1)
            cv2.circle(frame, target_position, 20, (0, 0, 255), -1)
            target_active = target_active ** 2 # ターゲット表示した
                        
        if alert_start:
            elapsed_time = time.time() - start_time
            if elapsed_time > time_duration and score < clear_score:
                # タイムアウトとスコアがクリアされていない場合にメッセージを表示して終了
                # alert_active[seek_ids.index(marker_id)] = 2
                alert_active[0] = 2
                cv2.putText(frame, "Your thing has been stolen", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
                cv2.imshow('Marker Catch', frame)
                # cv2.waitKey(10000)  # 10秒間表示
                # break  # システム終了

        # 検出されなくなったIDを確認して「Your thing has been stolen」を表示
        disappeared_ids = previous_ids - detected_ids
        if disappeared_ids:
            for marker_id in disappeared_ids:
                if alert_active[seek_ids.index(marker_id)] == 0:
                    alert_active[seek_ids.index(marker_id)] = 1
                 # マーカーが消えた場合、アラートを「スコア」に設定
            if not alert_start:
                start_time = time.time()
                alert_start = True
                play_alert_sound('alert_sound.mp3')  # 音を再生
                change_volume('alert_sound.mp3', 1)

        # 「Your thing has been stolen」をフレームに表示
        if 2 in alert_active:
            stop_alert_sound('alert_sound')
            play_alert_sound('siren.mp3')
            cv2.putText(frame, "Your thing has been stolen", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

        # マーカー動きアラートをフレームに表示
        if 1 in alert_active:
            moving_ids = []
            moving_items = ''
            if time.time() % 10 < 5:
                print(alert_active)
            for i in range(len(alert_active)):
                if alert_active[i] == 1:
                    moving_ids.append(seek_ids[i])
                    moving_items = moving_items +  ',' + marker_names[seek_ids[i]]
            cv2.putText(frame, f"alarm on {moving_items}!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

    # フレームを表示
        cv2.imshow('Marker Catch', frame)

        # キー入力で終了またはゲーム開始
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('s') and waiting_for_start:
            waiting_for_start = False
    
        # 前のフレームのIDを更新
        previous_ids = detected_ids.copy()

pygame.mixer.quit()
cap.release()
cv2.destroyAllWindows()
