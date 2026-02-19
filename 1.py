import cv2
import numpy as np
import random
import time
import pygame  
import threading

# ランダムにターゲット位置を生成する関数
def get_random_target_position(frame_shape):
    height, width, _ = frame_shape  # フレームの高さと幅を取得
    x = random.randint(50, width - 50)  # x座標をランダムに生成（50pxのマージン）
    y = random.randint(50, height - 50)  # y座標をランダムに生成（50pxのマージン）
    return (x, y)  # 生成したターゲット位置を返す

# アラート音を再生する関数
def play_alert_sound():
    # 別スレッドでアラート音を再生
    threading.Thread(target=pygame.mixer.Sound('alert_sound.mp3').play, daemon=True).start()

# pygameのサウンド機能を初期化
pygame.mixer.init()

# ArUcoマーカーの辞書を設定（4x4マーカー、50種類）
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
# マーカーの検出パラメータを設定
parameters = cv2.aruco.DetectorParameters()

# 監視対象のマーカーIDリスト
seek_ids = [0, 1, 2, 3, 4, 5, 6, 7, 8]
# 各マーカーIDに対応する名前を設定
marker_names = {
    0: "smartphone",
    1: "wallet",
    2: "PC"
}

# カメラの初期化（カメラインデックス1を使用）
cap = cv2.VideoCapture(1)

# スコアと制限時間の設定
score = 0  # 初期スコアは0
time_duration = 15  # 制限時間（15秒）
clear_score = 3  # クリアに必要なスコア（3点）
start_time = None  # スタート時間は最初はNone

# アラート状態の管理（マーカーごとに状態を管理）
alert_active = [0] * len(seek_ids)  # アラートの状態を保持
target_active = -1  # 現在アクティブなターゲットを管理（-1で無効）
detected_ids = set()  # 現在のフレームで検出されたIDを追跡
previous_ids = set()  # 前のフレームで検出されたIDを追跡

# ランダムなターゲット位置を生成
target_position = get_random_target_position(cap.read()[1].shape)
# マーカーの位置履歴を保存する辞書
previous_marker_positions = {}

# 待機状態の管理フラグ（ゲームが開始されるまで待機）
waiting_for_start = True

# メインループ（カメラの映像を読み取り処理）
while True:
    ret, frame = cap.read()  # カメラからフレームを取得
    if not ret:  # フレームが取得できなければループを終了
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # カラーフレームをグレースケールに変換
    corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)  # ArUcoマーカーを検出

    # 待機状態の場合
    if waiting_for_start:
        # 待機状態で「システム開始のためのsキー」を表示
        cv2.putText(frame, "Please press s to start security system", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
    else:
        detected_ids.clear()  # 現在のフレームで検出されたIDをリセット

        if ids is not None:  # マーカーが検出された場合
            for i in range(len(ids)):
                marker_id = ids[i][0]  # 現在検出されたマーカーのID

                # 監視対象ID（0〜8）に対して処理を実行
                if marker_id in seek_ids:
                    detected_ids.add(marker_id)  # 検出されたIDをセットに追加
                    corner = corners[i][0]  # 検出されたマーカーのコーナー情報
                    x = int((corner[0][0] + corner[2][0]) / 2)  # マーカーの中心x座標
                    y = int((corner[0][1] + corner[2][1]) / 2)  # マーカーの中心y座標
                    cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)  # マーカー中心に緑の円を描画

                    # マーカーの名前を表示
                    if marker_id in marker_names:
                        label = marker_names[marker_id]
                        cv2.putText(frame, label, (x + 10, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)

                    # マーカーの移動を追跡
                    if marker_id in previous_marker_positions:
                        prev_x, prev_y = previous_marker_positions[marker_id]  # 前回のマーカー位置
                        movement_distance = np.sqrt((x - prev_x) ** 2 + (y - prev_y) ** 2)  # 移動距離を計算

                        # 移動距離がしきい値を超えた場合にアラートを発動
                        if movement_distance > 10 and score < clear_score:
                            alert_active[marker_id] = 1  # アラート状態を設定
                            play_alert_sound()  # アラート音を再生
                            start_time = time.time()  # スタート時間を設定

                    previous_marker_positions[marker_id] = (x, y)  # 現在のマーカー位置を保存

                    # アラート状態に応じてターゲットを表示
                    if 1 in alert_active:
                        cv2.circle(frame, target_position, 20, (0, 0, 255), -1)  # ターゲット位置に赤い円を描画
                        target_active = target_active ** 2  # ターゲットアクティブ状態を切り替え

                    # マーカーがターゲットに近づいた場合、スコアを加算
                    distance = np.sqrt((x - target_position[0]) ** 2 + (y - target_position[1]) ** 2)
                    if distance < 30 and (2 not in alert_active):  # 近づいた場合
                        score += 1  # スコアを加算
                        target_position = get_random_target_position(frame.shape)  # 新しいターゲット位置を生成
                        target_active = -1  # ターゲットの状態をリセット
                        if score >= clear_score:  # 目標スコアに到達した場合
                            alert_active = [-1] * len(alert_active)  # アラート状態をリセット
                            target_active = 0  # ターゲットアクティブ状態をリセット
                            waiting_for_start = True  # スコア達成後に再度待機状態に戻す
                            score = 0  # スコアをリセット
                            print("Goal score reached! System waiting...")  # 目標スコア達成メッセージを表示

        # 制限時間を計測
        if start_time is not None:
            elapsed_time = time.time() - start_time  # 経過時間を計算
            if elapsed_time > time_duration and score < clear_score:  # 制限時間を超えた場合
                cv2.putText(frame, "Your thing has been stolen", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
                cv2.imshow('Marker Catch', frame)  # メッセージをフレームに表示
                cv2.waitKey(10000)  # 10秒間表示
                break  # システム終了

        # マーカーが消えた場合の処理
        disappeared_ids = previous_ids - detected_ids  # 消失したIDを確認
        if disappeared_ids:
            for marker_id in disappeared_ids:
                alert_active[marker_id] = 2  # アラート状態を「盗まれた」に設定
            play_alert_sound()  # アラート音を再生

        # 「Your thing has been stolen」のメッセージをフレームに表示
        if score < clear_score and alert_active[0] == 2:
            cv2.putText(frame, "Your thing has been stolen", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

        # フレームを表示
        cv2.imshow('Marker Catch', frame)

        previous_ids = detected_ids  # 現在検出されたIDを前のIDとして保存

    # ユーザーが's'キーを押すとシステムを開始
    key = cv2.waitKey(1) & 0xFF
    if key == ord('s'):
        waiting_for_start = False  # システム開始フラグを設定
    elif key == ord('q'):  # 'q'キーでシステムを終了
        break

# カメラをリリースしてウィンドウを閉じる
cap.release()
cv2.destroyAllWindows()
