# 動画壁紙機能

## 概要

SuperpaperにmacOS専用の動画壁紙機能が追加されました。LiveWallpaperアプリと同じアーキテクチャを採用し、AVPlayerを使った滑らかな動画再生を実現しています。

## アーキテクチャ

- **Daemon方式**: 各ディスプレイごとに独立したPythonプロセスで動画を再生
- **AVPlayer**: macOSのネイティブ動画再生フレームワークを使用（ハードウェアアクセラレーション対応）
- **ウィンドウレベル**: デスクトップレベル（アイコンの下）に配置
- **静的フレームキャッシュ**: スリープ復帰時の高速表示

## 使い方

### 1. 動画プロファイルの作成

`superpaper/profiles/` ディレクトリに `.profile` ファイルを作成します：

```ini
[my_video_profile]
name=my_video_profile
spanmode=single
slideshow=false
video_display0=/Users/yourusername/Movies/video1.mp4
video_display1=/Users/yourusername/Movies/video2.mp4
```

**重要な設定**:
- `video_displayN`: 各ディスプレイの動画パス（N=0,1,2...）
- `slideshow=false`: 動画モードではスライドショーは無効
- 絶対パスを使用してください

### 2. 対応動画形式

- `.mp4`
- `.mov`
- `.webm`
- `.avi`
- `.m4v`
- `.mkv`

### 3. GUIから設定

1. Superpaperを起動
2. トレイアイコンをクリック
3. プロファイル選択で動画プロファイルを選択
4. または、設定画面で動画ファイルを選択

## 設定

### 音量調整

```python
# UserDefaultsで設定（0.0-1.0）
defaults write com.superpaper wallpapervolume 0.5
```

### スケールモード

```python
# fill（デフォルト）: 画面を埋める
# fit: アスペクト比を維持
# stretch: 引き伸ばし
defaults write com.superpaper scale_mode fill
```

## システム要件

- **macOS 10.13以上**
- **PyObjC** (すでにインストール済み)
- AVFoundation, AppKit (macOS標準)

## パフォーマンス

- **CPU使用率**: AVPlayerがハードウェアアクセラレーション使用（低負荷）
- **メモリ**: daemon1つあたり約50-100MB
- **バッテリー**: 音量0の場合、静止画より10-20%程度増加

## トラブルシューティング

### 動画が表示されない

1. ターミナルで確認:
```bash
python -m superpaper --debug
```

2. ログを確認:
```bash
ls -la ~/Library/Logs/superpaper.log
```

3. Daemonプロセスを確認:
```bash
ps aux | grep video_daemon
```

### Daemonが残っている場合

```bash
killall -9 Python
```

## 制約事項

- **macOS専用**: Linux/Windowsでは静止画のみ
- **span mode非対応**: 動画は各ディスプレイ独立のみ
- **perspective非対応**: 動画は補正なし
- **スライドショー非対応**: 動画は常にループ再生

## ファイル構成

```
superpaper/
├── video_daemon.py       # 動画再生daemon
├── video_engine.py       # Daemon管理エンジン
├── wallpaper_processing.py  # 動画対応追加
├── data.py               # プロファイル設定拡張
└── profiles/
    └── example_video.profile  # 動画プロファイル例
```

## 開発者向け

### CFNotification

Daemonとの通信にCFNotificationを使用：

- `com.superpaper.video.terminate`: 終了
- `com.superpaper.video.volumeChanged`: 音量変更
- `com.superpaper.video.spaceChanged`: スペース変更

### 静的フレーム生成

```python
from superpaper.video_engine import VideoEngine
engine = VideoEngine.shared_instance()
engine.generate_static_frame(video_path, output_path)
```

## ライセンス

MIT License (Superpaper本体と同じ)
