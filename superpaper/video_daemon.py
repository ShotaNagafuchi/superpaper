"""
Video Wallpaper Daemon for Superpaper on macOS.

This daemon runs as a separate process and plays video wallpapers
using AVPlayer in a window positioned at desktop level.

Inspired by LiveWallpaper app architecture.
"""

import sys
import signal
import os
from threading import Thread

from Foundation import (
    NSObject, NSURL, NSNotificationCenter,
    CFNotificationCenterGetDarwinNotifyCenter,
    CFNotificationCenterAddObserver,
    kCFNotificationDeliverImmediately,
    kCFNotificationPostToAllSessions
)
from AppKit import (
    NSApplication, NSWindow, NSView, NSScreen,
    NSBackingStoreBuffered, NSWindowStyleMaskBorderless,
    NSColor, NSImage
)
from AVFoundation import (
    AVPlayer, AVPlayerLayer, AVPlayerItem,
    AVLayerVideoGravityResize, AVLayerVideoGravityResizeAspect,
    AVLayerVideoGravityResizeAspectFill
)
from Quartz import (
    CGWindowLevelForKey, kCGDesktopWindowLevelKey,
    CGDisplayBounds
)
import objc


class VideoWallpaperWindow(NSWindow):
    """Window that displays video at desktop wallpaper level."""
    
    def initWithScreen_videoPath_staticPath_volume_scaleMode_(
        self, screen, video_path, static_path, volume, scale_mode
    ):
        """Initialize video wallpaper window."""
        # Get screen frame
        frame = screen.frame()
        
        # Create window at desktop level
        self = objc.super(VideoWallpaperWindow, self).initWithContentRect_styleMask_backing_defer_(
            frame,
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False
        )
        
        if self is None:
            return None
        
        # Configure window
        self.setBackgroundColor_(NSColor.blackColor())
        self.setOpaque_(True)
        self.setLevel_(CGWindowLevelForKey(kCGDesktopWindowLevelKey))
        self.setCollectionBehavior_(1 << 8)  # NSWindowCollectionBehaviorCanJoinAllSpaces
        self.setIgnoresMouseEvents_(True)
        
        # Store parameters
        self.video_path = video_path
        self.static_path = static_path
        self.current_volume = volume
        self.scale_mode = scale_mode
        
        # Create player view
        self.setupVideoPlayer()
        
        # Show static image first (for faster startup)
        if static_path and os.path.exists(static_path):
            self.showStaticImage()
        
        # Start video playback
        self.startVideo()
        
        return self
    
    def setupVideoPlayer(self):
        """Setup AVPlayer and layer."""
        # Create player
        video_url = NSURL.fileURLWithPath_(self.video_path)
        self.player_item = AVPlayerItem.playerItemWithURL_(video_url)
        self.player = AVPlayer.playerWithPlayerItem_(self.player_item)
        
        # Set volume
        self.player.setVolume_(self.current_volume)
        
        # Create player layer
        self.player_layer = AVPlayerLayer.playerLayerWithPlayer_(self.player)
        
        # Set scale mode
        if self.scale_mode == "fill":
            self.player_layer.setVideoGravity_(AVLayerVideoGravityResizeAspectFill)
        elif self.scale_mode == "fit":
            self.player_layer.setVideoGravity_(AVLayerVideoGravityResizeAspect)
        else:
            self.player_layer.setVideoGravity_(AVLayerVideoGravityResize)
        
        # Set layer frame
        self.player_layer.setFrame_(self.contentView().bounds())
        
        # Add layer to window
        self.contentView().setWantsLayer_(True)
        self.contentView().layer().addSublayer_(self.player_layer)
        
        # Setup loop notification
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self,
            "playerItemDidReachEnd:",
            "AVPlayerItemDidPlayToEndTimeNotification",
            self.player_item
        )
    
    def showStaticImage(self):
        """Show static image while video loads."""
        try:
            static_image = NSImage.alloc().initWithContentsOfFile_(self.static_path)
            if static_image:
                image_view = NSView.alloc().initWithFrame_(self.contentView().bounds())
                image_view.setWantsLayer_(True)
                image_view.layer().setContents_(static_image)
                self.contentView().addSubview_(image_view)
        except Exception as e:
            print(f"Failed to load static image: {e}")
    
    def startVideo(self):
        """Start video playback."""
        self.player.play()
    
    def playerItemDidReachEnd_(self, notification):
        """Loop video when it reaches the end."""
        from CoreMedia import kCMTimeZero
        self.player.seekToTime_(kCMTimeZero)
        self.player.play()
    
    def updateVolume_(self, new_volume):
        """Update playback volume."""
        self.current_volume = new_volume
        if self.player:
            self.player.setVolume_(new_volume)
    
    def cleanup(self):
        """Cleanup resources."""
        if self.player:
            self.player.pause()
        NSNotificationCenter.defaultCenter().removeObserver_(self)


class VideoDaemonDelegate(NSObject):
    """Application delegate for video daemon."""
    
    def initWithWindow_(self, window):
        """Initialize delegate with window."""
        self = objc.super(VideoDaemonDelegate, self).init()
        if self is None:
            return None
        
        self.window = window
        self.setupNotifications()
        return self
    
    def setupNotifications(self):
        """Setup CFNotification observers for IPC."""
        # CFNotification callbacks don't work well as instance methods in PyObjC
        # We'll use NSNotificationCenter for local notifications instead
        # For now, we'll skip CFNotification and rely on process signals
        pass
        # Note: Terminate will be handled by signal handlers
        # Volume and space changes are not critical for basic functionality
    
    def applicationDidFinishLaunching_(self, notification):
        """Called when application finishes launching."""
        print("Video daemon started successfully")


def signal_handler(signum, frame):
    """Handle termination signals."""
    print(f"Received signal {signum}, terminating...")
    NSApplication.sharedApplication().terminate_(None)


def main():
    """Main entry point for video daemon."""
    if len(sys.argv) < 6:
        print("Usage: video_daemon.py <video_path> <static_path> <volume> <scale_mode> <display_id>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    static_path = sys.argv[2]
    volume = float(sys.argv[3])
    scale_mode = sys.argv[4]
    display_id = int(sys.argv[5]) if sys.argv[5] else 0
    
    print(f"Starting video daemon:")
    print(f"  Video: {video_path}")
    print(f"  Static: {static_path}")
    print(f"  Volume: {volume}")
    print(f"  Scale: {scale_mode}")
    print(f"  Display: {display_id}")
    
    # Verify video file exists
    if not os.path.exists(video_path):
        print(f"ERROR: Video file not found: {video_path}")
        sys.exit(1)
    
    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create application
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(2)  # NSApplicationActivationPolicyAccessory
    
    # Find target screen
    screens = NSScreen.screens()
    target_screen = None
    
    for screen in screens:
        screen_dict = screen.deviceDescription()
        screen_number = screen_dict.get("NSScreenNumber", 0)
        if screen_number == display_id:
            target_screen = screen
            break
    
    if target_screen is None:
        print(f"WARNING: Display {display_id} not found, using main screen")
        target_screen = NSScreen.mainScreen()
    
    # Create video window
    window = VideoWallpaperWindow.alloc().initWithScreen_videoPath_staticPath_volume_scaleMode_(
        target_screen,
        video_path,
        static_path,
        volume,
        scale_mode
    )
    
    if window is None:
        print("ERROR: Failed to create video window")
        sys.exit(1)
    
    window.makeKeyAndOrderFront_(None)
    
    # Create and set delegate
    delegate = VideoDaemonDelegate.alloc().initWithWindow_(window)
    app.setDelegate_(delegate)
    
    # Run application
    print("Entering main loop...")
    app.run()


if __name__ == "__main__":
    main()
