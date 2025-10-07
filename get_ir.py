import cwiid
import time

print("Wiiリモコンの1+2ボタンを押してペアリングしてください...")
wm = None
while not wm:
    try:
        wm = cwiid.Wiimote()
    except RuntimeError:
        print("接続失敗。再試行中...")
        time.sleep(1)

print("接続成功！")
wm.rpt_mode = cwiid.RPT_IR

try:
    while True:
        ir = wm.state.get('ir_src', [])
        print("IRセンサー値:", ir)
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\n終了します")
    wm.close()
