"""
Video Wallpaper Window for Superpaper on macOS.

Manages video wallpaper windows in the main application process.
Based on LiveWallpaperMacOS architecture.
"""

import os
from Foundation import (
    NSObject, NSURL, NSUserDefaults, NSScreen, NSRunLoop,
    NSDefaultRunLoopMode, NSRunLoopCommonModes, NSTimer,
    NSNotificationCenter, NSWorkspace
)
from AppKit import (
    NSWindow, NSWindowStyleMaskBorderless, NSBackingStoreBuffered,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorStationary,
    NSWindowCollectionBehaviorIgnoresCycle,
    NSColor, NSWindowSharingNone
)
from AVFoundation import (
    AVAsset, AVPlayerItem, AVQueuePlayer, AVPlayerLooper, AVPlayerLayer,
    AVLayerVideoGravityResizeAspectFill, AVLayerVideoGravityResizeAspect,
    AVLayerVideoGravityResize
)
from Quartz import CGWindowLevelForKey, kCGDesktopWindowLevelKey, CGDisplayBounds
from objc import super as objc_super
import superpaper.sp_logging as sp_logging


class SPVideoWallpaperWindow(NSObject):
    """
    Video wallpaper window that plays video on the desktop.
    Runs in the main application process.
    """
    
    @classmethod
    def createWithVideo_screen_volume_scaleMode_cropRect_(cls, video_path, screen, volume, scale_mode, crop_rect):
        """
        Factory method to create a video wallpaper window.
        
        Args:
            video_path: Path to video file
            screen: NSScreen object for target display
            volume: Audio volume (0.0 to 1.0)
            scale_mode: Scaling mode ('fill', 'fit', 'stretch')
            crop_rect: Tuple (x, y, width, height) as normalized coordinates (0.0-1.0) for cropping
        
        Returns:
            SPVideoWallpaperWindow instance or None if failed
        """
        instance = cls.alloc().init()
        if instance.setupWithVideo_screen_volume_scaleMode_cropRect_(video_path, screen, volume, scale_mode, crop_rect):
            return instance
        return None
    
    def init(self):
        """Initialize the window."""
        self = objc_super(SPVideoWallpaperWindow, self).init()
        if self is None:
            return None
        
        self.window = None
        self.player = None
        self.player_layer = None
        self.looper = None
        self.target_screen = None
        
        return self
    
    def setupWithVideo_screen_volume_scaleMode_cropRect_(self, video_path, screen, volume, scale_mode, crop_rect):
        """
        Setup wallpaper with video.
        
        Args:
            video_path: Path to video file
            screen: NSScreen object
            volume: Audio volume
            scale_mode: Scaling mode
            crop_rect: Tuple (x, y, width, height) as normalized coordinates (0.0-1.0) for cropping, or None for full video
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # #region agent log
            import json; log_data = {"sessionId": "debug-session", "runId": "setup", "hypothesisId": "H1,H4,H5", "location": "video_wallpaper_window.py:setupWithVideo:entry", "message": "Setup entry", "data": {"video_path": video_path, "video_exists": os.path.exists(video_path), "file_size_mb": os.path.getsize(video_path) / (1024*1024) if os.path.exists(video_path) else 0}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
            # #endregion
            
            if not os.path.exists(video_path):
                sp_logging.G_LOGGER.error(f"Video file not found: {video_path}")
                return False
            
            self.target_screen = screen
            video_url = NSURL.fileURLWithPath_(video_path)
            visible_frame = screen.frame()
            
            # #region agent log
            import json; log_data = {"sessionId": "debug-session", "runId": "setup", "hypothesisId": "H1", "location": "video_wallpaper_window.py:setupWithVideo:url_created", "message": "Video URL created", "data": {"url": str(video_url)}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
            # #endregion
            
            # Create borderless window
            self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_screen_(
                visible_frame,
                NSWindowStyleMaskBorderless,
                NSBackingStoreBuffered,
                False,
                screen
            )
            
            # Set window to desktop level
            desktop_level = CGWindowLevelForKey(kCGDesktopWindowLevelKey)
            self.window.setLevel_(desktop_level - 1)
            
            # Configure window behavior
            self.window.setCollectionBehavior_(
                NSWindowCollectionBehaviorCanJoinAllSpaces |
                NSWindowCollectionBehaviorFullScreenAuxiliary |
                NSWindowCollectionBehaviorStationary |
                NSWindowCollectionBehaviorIgnoresCycle
            )
            
            self.window.setOpaque_(False)
            self.window.setBackgroundColor_(NSColor.clearColor())
            self.window.setHasShadow_(False)
            self.window.contentView().setWantsLayer_(True)
            self.window.setSharingType_(NSWindowSharingNone)
            self.window.setIgnoresMouseEvents_(True)
            
            # Create AVPlayer with looper
            # #region agent log
            import json; log_data = {"sessionId": "debug-session", "runId": "setup", "hypothesisId": "H1,H4", "location": "video_wallpaper_window.py:setupWithVideo:before_asset", "message": "Before creating AVAsset", "data": {}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
            # #endregion
            
            asset = AVAsset.assetWithURL_(video_url)
            
            # #region agent log
            import json; log_data = {"sessionId": "debug-session", "runId": "setup", "hypothesisId": "H1,H4", "location": "video_wallpaper_window.py:setupWithVideo:asset_created", "message": "AVAsset created", "data": {}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
            # #endregion
            
            item = AVPlayerItem.playerItemWithAsset_(asset)
            
            # #region agent log
            import json; log_data = {"sessionId": "debug-session", "runId": "setup", "hypothesisId": "H1,H4", "location": "video_wallpaper_window.py:setupWithVideo:item_created", "message": "AVPlayerItem created", "data": {}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
            # #endregion
            
            self.player = AVQueuePlayer.queuePlayerWithItems_([])
            
            # #region agent log
            import json; log_data = {"sessionId": "debug-session", "runId": "setup", "hypothesisId": "H1,H4", "location": "video_wallpaper_window.py:setupWithVideo:player_created", "message": "AVQueuePlayer created", "data": {}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
            # #endregion
            
            self.looper = AVPlayerLooper.playerLooperWithPlayer_templateItem_(
                self.player, item
            )
            
            # #region agent log
            import json; log_data = {"sessionId": "debug-session", "runId": "setup", "hypothesisId": "H1,H4", "location": "video_wallpaper_window.py:setupWithVideo:looper_created", "message": "AVPlayerLooper created", "data": {}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
            # #endregion
            
            # Create and configure player layer
            self.player_layer = AVPlayerLayer.playerLayerWithPlayer_(self.player)
            
            # For spanning: set video gravity to fill and disable cropping
            # We'll use a different approach - scale the layer to canvas size and offset it
            self.player_layer.setVideoGravity_(AVLayerVideoGravityResizeAspectFill)
            
            # Store crop info for later use
            self.crop_info = crop_rect
            
            if crop_rect is not None:
                # Spanning mode: scale player layer to entire canvas size
                # and position it so the correct portion shows in this window
                from Quartz import CGRectMake
                x_norm, y_norm, width_norm, height_norm = crop_rect
                
                # Get window bounds
                window_bounds = self.window.contentView().bounds()
                window_width = window_bounds.size.width
                window_height = window_bounds.size.height
                
                # Calculate canvas size from normalized crop dimensions
                # window_width = canvas_width * width_norm
                canvas_width = window_width / width_norm if width_norm > 0 else window_width
                canvas_height = window_height / height_norm if height_norm > 0 else window_height
                
                # Calculate offset - where to position the canvas within this window
                # The portion at (x_norm, y_norm) of the canvas should be at (0, 0) of the window
                offset_x = -x_norm * canvas_width
                offset_y = -y_norm * canvas_height
                
                # Set player layer frame to full canvas size, positioned with offset
                layer_frame = CGRectMake(offset_x, offset_y, canvas_width, canvas_height)
                self.player_layer.setFrame_(layer_frame)
                
                # Enable clipping to window bounds
                self.window.contentView().layer().setMasksToBounds_(True)
                
                # #region agent log
                import json; log_data = {"sessionId": "debug-session", "runId": "span", "hypothesisId": "H9_FIX", "location": "video_wallpaper_window.py:setupWithVideo:layer_transform", "message": "Applied layer scaling and offset", "data": {"crop_x": float(x_norm), "crop_y": float(y_norm), "crop_w": float(width_norm), "crop_h": float(height_norm), "window_w": float(window_width), "window_h": float(window_height), "canvas_w": float(canvas_width), "canvas_h": float(canvas_height), "offset_x": float(offset_x), "offset_y": float(offset_y)}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
                # #endregion
                
                sp_logging.G_LOGGER.info(f"Applied layer transform: canvas={canvas_width:.0f}x{canvas_height:.0f}, offset=({offset_x:.0f},{offset_y:.0f})")
            else:
                # Non-spanning mode: just fill the window
                self.player_layer.setFrame_(self.window.contentView().bounds())
            
            self.window.contentView().layer().addSublayer_(self.player_layer)
            
            # Set window frame and show
            self.window.setFrame_display_(visible_frame, True)
            self.window.makeKeyAndOrderFront_(None)
            
            # #region agent log
            import json; log_data = {"sessionId": "debug-session", "runId": "setup", "hypothesisId": "H4", "location": "video_wallpaper_window.py:setupWithVideo:before_play", "message": "Before player.play()", "data": {}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
            # #endregion
            
            # Configure and start playback
            self.player.setVolume_(volume)
            self.player.setMuted_(False)
            self.player.play()
            
            # #region agent log
            import json; log_data = {"sessionId": "debug-session", "runId": "setup", "hypothesisId": "H4", "location": "video_wallpaper_window.py:setupWithVideo:after_play", "message": "After player.play()", "data": {}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
            # #endregion
            
            sp_logging.G_LOGGER.info(f"Video wallpaper window created for screen {screen}")
            return True
            
        except Exception as e:
            sp_logging.G_LOGGER.error(f"Failed to setup video wallpaper window: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def cleanup(self):
        """Cleanup and close the window."""
        # #region agent log
        import json; log_data = {"sessionId": "debug-session", "runId": "cleanup", "hypothesisId": "H2", "location": "video_wallpaper_window.py:cleanup:entry", "message": "Starting cleanup", "data": {"has_player": self.player is not None, "has_window": self.window is not None}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
        # #endregion
        
        if self.player:
            self.player.pause()
            # #region agent log
            import json; log_data = {"sessionId": "debug-session", "runId": "cleanup", "hypothesisId": "H2", "location": "video_wallpaper_window.py:cleanup:player_paused", "message": "Player paused", "data": {}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
            # #endregion
        
        # Remove layer before closing window
        if self.player_layer and self.window:
            self.player_layer.removeFromSuperlayer()
            # #region agent log
            import json; log_data = {"sessionId": "debug-session", "runId": "cleanup", "hypothesisId": "H2", "location": "video_wallpaper_window.py:cleanup:layer_removed", "message": "Layer removed", "data": {}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
            # #endregion
        
        if self.window:
            self.window.setReleasedWhenClosed_(True)
            self.window.close()
            # #region agent log
            import json; log_data = {"sessionId": "debug-session", "runId": "cleanup", "hypothesisId": "H2", "location": "video_wallpaper_window.py:cleanup:window_closed", "message": "Window closed", "data": {}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
            # #endregion
            self.window = None
        
        # #region agent log
        import json; log_data = {"sessionId": "debug-session", "runId": "cleanup", "hypothesisId": "H2", "location": "video_wallpaper_window.py:cleanup:before_clear_refs", "message": "Before clearing references", "data": {}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
        # #endregion
        
        self.looper = None
        self.player = None
        self.player_layer = None
        
        # #region agent log
        import json; log_data = {"sessionId": "debug-session", "runId": "cleanup", "hypothesisId": "H2", "location": "video_wallpaper_window.py:cleanup:complete", "message": "Cleanup complete", "data": {}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
        # #endregion
        
        sp_logging.G_LOGGER.info("Video wallpaper window cleaned up")


class SPVideoWallpaperManager(NSObject):
    """
    Manages multiple video wallpaper windows.
    Singleton instance in the main application process.
    """
    
    _shared_instance = None
    
    @classmethod
    def sharedManager(cls):
        """Get or create shared manager instance."""
        if cls._shared_instance is None:
            cls._shared_instance = cls.alloc().init()
        return cls._shared_instance
    
    def init(self):
        """Initialize the manager."""
        self = objc_super(SPVideoWallpaperManager, self).init()
        if self is None:
            return None
        
        self.windows = []
        sp_logging.G_LOGGER.info("SPVideoWallpaperManager initialized")
        return self
    
    def startWallpaperWithPaths_displayIDs_volume_scaleMode_(self, video_paths, display_ids, volume, scale_mode):
        """
        Start video wallpapers on specified displays.
        
        For spanning mode (one video across multiple displays):
        - If all video_paths are the same, span that video across all displays
        - Otherwise, play separate videos on each display
        
        Args:
            video_paths: List of video file paths
            display_ids: List of CGDirectDisplayIDs
            volume: Audio volume
            scale_mode: Scaling mode
        
        Returns:
            True if at least one window was created successfully
        """
        # Clean up existing windows first
        self.stopAllWallpapers()
        
        # Check if we should span a single video across all displays
        is_spanning = len(set(video_paths)) == 1 and len(video_paths) > 1
        
        if is_spanning:
            # Span mode: one video across multiple displays
            sp_logging.G_LOGGER.info(f"Spanning video across {len(display_ids)} displays")
            return self.__start_spanned_wallpaper(video_paths[0], display_ids, volume, scale_mode)
        else:
            # Individual mode: separate video for each display
            sp_logging.G_LOGGER.info(f"Playing individual videos on {len(display_ids)} displays")
            return self.__start_individual_wallpapers(video_paths, display_ids, volume, scale_mode)
    
    def __start_spanned_wallpaper(self, video_path, display_ids, volume, scale_mode):
        """
        Start a single video spanned across multiple displays.
        
        Args:
            video_path: Path to video file
            display_ids: List of CGDirectDisplayIDs
            volume: Audio volume
            scale_mode: Scaling mode
        
        Returns:
            True if successful
        """
        # #region agent log
        import json; log_data = {"sessionId": "debug-session", "runId": "span", "hypothesisId": "H1", "location": "video_wallpaper_window.py:__start_spanned_wallpaper:entry", "message": "Starting spanned wallpaper", "data": {"video_path": video_path, "display_ids": display_ids, "volume": volume, "scale_mode": scale_mode}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
        # #endregion
        
        # #region agent log
        all_screens_info = []
        for idx, ns_screen in enumerate(NSScreen.screens()):
            screen_dict = ns_screen.deviceDescription()
            screen_number = screen_dict.get("NSScreenNumber", None)
            frame = ns_screen.frame()
            all_screens_info.append({"index": idx, "NSScreenNumber": int(screen_number) if screen_number else None, "origin_x": float(frame.origin.x), "origin_y": float(frame.origin.y), "width": float(frame.size.width), "height": float(frame.size.height)})
        import json; log_data = {"sessionId": "debug-session", "runId": "span", "hypothesisId": "H8", "location": "video_wallpaper_window.py:__start_spanned_wallpaper:all_screens", "message": "All available NSScreens", "data": {"screens_count": len(all_screens_info), "screens": all_screens_info}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
        # #endregion
        
        # Get all screens and calculate the bounding canvas
        screens = []
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')
        
        for display_id in display_ids:
            # display_id is actually an index into NSScreen.screens(), not NSScreenNumber
            all_ns_screens = NSScreen.screens()
            if display_id >= len(all_ns_screens):
                sp_logging.G_LOGGER.warning(f"Display index {display_id} out of range (only {len(all_ns_screens)} screens available)")
                continue
            
            screen = all_ns_screens[display_id]
            
            # #region agent log
            screen_dict = screen.deviceDescription()
            screen_number = screen_dict.get("NSScreenNumber", None)
            import json; log_data = {"sessionId": "debug-session", "runId": "span", "hypothesisId": "H6_FIX", "location": "video_wallpaper_window.py:__start_spanned_wallpaper:found_by_index", "message": f"Found screen by index {display_id}", "data": {"display_index": display_id, "screen_number": int(screen_number) if screen_number else None}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
            # #endregion
            
            frame = screen.frame()
            # #region agent log
            import json; log_data = {"sessionId": "debug-session", "runId": "span", "hypothesisId": "H5", "location": "video_wallpaper_window.py:__start_spanned_wallpaper:frame", "message": f"Screen frame for display {display_id}", "data": {"display_id": display_id, "origin_x": float(frame.origin.x), "origin_y": float(frame.origin.y), "width": float(frame.size.width), "height": float(frame.size.height)}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
            # #endregion
            
            screens.append((screen, display_id))
            min_x = min(min_x, frame.origin.x)
            min_y = min(min_y, frame.origin.y)
            max_x = max(max_x, frame.origin.x + frame.size.width)
            max_y = max(max_y, frame.origin.y + frame.size.height)
        
        if not screens:
            sp_logging.G_LOGGER.error("No screens found for spanning")
            return False
        
        # Calculate canvas dimensions
        canvas_width = max_x - min_x
        canvas_height = max_y - min_y
        
        # #region agent log
        import json; log_data = {"sessionId": "debug-session", "runId": "span", "hypothesisId": "H2", "location": "video_wallpaper_window.py:__start_spanned_wallpaper:canvas", "message": "Canvas calculated", "data": {"min_x": float(min_x), "min_y": float(min_y), "max_x": float(max_x), "max_y": float(max_y), "canvas_width": float(canvas_width), "canvas_height": float(canvas_height)}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
        # #endregion
        
        sp_logging.G_LOGGER.info(f"Canvas size: {canvas_width}x{canvas_height}")
        
        # Create a window for each display with appropriate crop rect
        success_count = 0
        for screen, display_id in screens:
            frame = screen.frame()
            
            # Calculate normalized crop rectangle for this display
            # Note: macOS coordinate system has origin at bottom-left
            crop_x = (frame.origin.x - min_x) / canvas_width
            crop_y = (frame.origin.y - min_y) / canvas_height
            crop_width = frame.size.width / canvas_width
            crop_height = frame.size.height / canvas_height
            
            crop_rect = (crop_x, crop_y, crop_width, crop_height)
            
            # #region agent log
            import json; log_data = {"sessionId": "debug-session", "runId": "span", "hypothesisId": "H3", "location": "video_wallpaper_window.py:__start_spanned_wallpaper:crop", "message": f"Crop rect for display {display_id}", "data": {"display_id": display_id, "frame_x": float(frame.origin.x), "frame_y": float(frame.origin.y), "frame_w": float(frame.size.width), "frame_h": float(frame.size.height), "crop_x": float(crop_x), "crop_y": float(crop_y), "crop_width": float(crop_width), "crop_height": float(crop_height)}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
            # #endregion
            
            sp_logging.G_LOGGER.info(
                f"Display {display_id}: pos=({frame.origin.x:.0f},{frame.origin.y:.0f}), "
                f"size=({frame.size.width:.0f}x{frame.size.height:.0f}), "
                f"crop=({crop_x:.3f},{crop_y:.3f},{crop_width:.3f},{crop_height:.3f})"
            )
            
            window = SPVideoWallpaperWindow.createWithVideo_screen_volume_scaleMode_cropRect_(
                video_path, screen, volume, scale_mode, crop_rect
            )
            
            if window:
                self.windows.append(window)
                success_count += 1
                sp_logging.G_LOGGER.info(f"Created spanned video window for display {display_id}")
            else:
                sp_logging.G_LOGGER.error(f"Failed to create window for display {display_id}")
        
        return success_count > 0
    
    def __start_individual_wallpapers(self, video_paths, display_ids, volume, scale_mode):
        """
        Start individual videos on each display.
        
        Args:
            video_paths: List of video file paths
            display_ids: List of CGDirectDisplayIDs
            volume: Audio volume
            scale_mode: Scaling mode
        
        Returns:
            True if at least one window was created successfully
        """
        success_count = 0
        
        for video_path, display_id in zip(video_paths, display_ids):
            # display_id is actually an index into NSScreen.screens()
            all_ns_screens = NSScreen.screens()
            if display_id >= len(all_ns_screens):
                sp_logging.G_LOGGER.warning(f"Display index {display_id} out of range, using main screen")
                screen = NSScreen.mainScreen()
            else:
                screen = all_ns_screens[display_id]
            
            # Create window without crop (full video on this display)
            window = SPVideoWallpaperWindow.createWithVideo_screen_volume_scaleMode_cropRect_(
                video_path, screen, volume, scale_mode, None
            )
            
            if window:
                self.windows.append(window)
                success_count += 1
                sp_logging.G_LOGGER.info(f"Started video wallpaper on display {display_id}")
            else:
                sp_logging.G_LOGGER.error(f"Failed to create video wallpaper window for display {display_id}")
        
        return success_count > 0
    
    def stopAllWallpapers(self):
        """Stop and cleanup all video wallpaper windows."""
        for window in self.windows:
            window.cleanup()
        
        self.windows = []
        sp_logging.G_LOGGER.info("All video wallpapers stopped")
