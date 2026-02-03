"""
Video Engine for Superpaper on macOS.

Manages video wallpaper daemons, generates static frames,
and handles inter-process communication.

Inspired by LiveWallpaper app architecture.
"""

import os
import sys
import subprocess
import signal
from pathlib import Path
from threading import Lock

from Foundation import (
    NSUserDefaults, NSURL,
    CFNotificationCenterGetDarwinNotifyCenter,
    CFNotificationCenterPostNotification,
    kCFNotificationDeliverImmediately,
    kCFNotificationPostToAllSessions
)
from AVFoundation import AVAsset, AVAssetImageGenerator
from CoreMedia import CMTimeMakeWithSeconds, CMTimeGetSeconds
from Quartz import CGImageDestinationCreateWithURL, CGImageDestinationAddImage, CGImageDestinationFinalize, CGSizeApplyAffineTransform

import superpaper.sp_logging as sp_logging
import superpaper.sp_paths as sp_paths
from superpaper.video_wallpaper_window import SPVideoWallpaperManager


class VideoEngine:
    """
    Singleton engine for managing video wallpaper daemons.
    """
    
    _instance = None
    _lock = Lock()
    
    @classmethod
    def shared_instance(cls):
        """Get or create shared instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize video engine."""
        if VideoEngine._instance is not None:
            raise RuntimeError("Use VideoEngine.shared_instance() instead")
        
        self.daemon_pids = []
        self.daemon_path = None
        self.static_cache_path = None
        self.setup_paths()
        
        # Default settings
        self.default_volume = 0.0  # Muted by default
        self.default_scale_mode = "fill"  # fill, fit, stretch
    
    def setup_paths(self):
        """Setup paths for daemon and cache."""
        # Daemon path - use Python interpreter to run video_daemon.py
        daemon_script = os.path.join(
            sp_paths.PATH,
            "superpaper",
            "video_daemon.py"
        )
        self.daemon_path = sys.executable  # Python interpreter
        self.daemon_script = daemon_script
        
        # Static cache path
        cache_base = os.path.expanduser("~/Library/Caches/Superpaper")
        self.static_cache_path = os.path.join(cache_base, "wallpapers")
        
        # Create cache directory if needed
        os.makedirs(self.static_cache_path, exist_ok=True)
        
        sp_logging.G_LOGGER.info(f"Video engine initialized:")
        sp_logging.G_LOGGER.info(f"  Daemon: {self.daemon_script}")
        sp_logging.G_LOGGER.info(f"  Cache: {self.static_cache_path}")
    
    def start_video_wallpaper(self, video_paths, display_ids):
        """
        Start video wallpaper on specified displays.
        
        Args:
            video_paths: List of video file paths (one per display)
            display_ids: List of display IDs
        """
        if len(video_paths) != len(display_ids):
            sp_logging.G_LOGGER.error(
                f"Mismatch: {len(video_paths)} videos for {len(display_ids)} displays"
            )
            return
        
        # Stop existing wallpapers first
        self.stop_video_wallpapers()
        
        # Get settings
        defaults = NSUserDefaults.standardUserDefaults()
        volume = defaults.floatForKey_("wallpapervolume") or self.default_volume
        scale_mode_str = defaults.stringForKey_("scale_mode") or self.default_scale_mode
        
        # Generate static frames for all videos
        for video_path in video_paths:
            if not os.path.exists(video_path):
                sp_logging.G_LOGGER.error(f"Video not found: {video_path}")
                return
            
            # Generate or get static frame (for quick display during transitions)
            self.get_or_generate_static_frame(video_path)
        
        # Start video wallpapers using SPVideoWallpaperManager
        manager = SPVideoWallpaperManager.sharedManager()
        success = manager.startWallpaperWithPaths_displayIDs_volume_scaleMode_(
            video_paths, display_ids, volume, scale_mode_str
        )
        
        if success:
            sp_logging.G_LOGGER.info(
                f"Started video wallpaper on {len(display_ids)} display(s)"
            )
        else:
            sp_logging.G_LOGGER.error("Failed to start video wallpapers")
    
    def launch_daemon(self, video_path, static_path, volume, scale_mode, display_id):
        """
        Launch a single video daemon process.
        
        Returns:
            Process ID if successful, None otherwise
        """
        # #region agent log
        import json; log_data = {"sessionId": "debug-session", "runId": "initial", "hypothesisId": "daemon", "location": "video_engine.py:launch_daemon:135", "message": "launch_daemon: entry", "data": {"video_path": video_path, "static_path": static_path, "volume": volume, "scale_mode": scale_mode, "display_id": display_id}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
        # #endregion
        if not os.path.exists(self.daemon_script):
            sp_logging.G_LOGGER.error(f"Daemon script not found: {self.daemon_script}")
            return None
        
        try:
            # Build command
            cmd = [
                self.daemon_path,  # Python interpreter
                self.daemon_script,  # video_daemon.py
                video_path,
                static_path,
                str(volume),
                scale_mode,
                str(display_id)
            ]
            
            # #region agent log
            import json; log_data = {"sessionId": "debug-session", "runId": "initial", "hypothesisId": "daemon", "location": "video_engine.py:launch_daemon:152", "message": "launch_daemon: before Popen", "data": {"cmd": cmd}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
            # #endregion
            
            sp_logging.G_LOGGER.info(f"Launching daemon: {' '.join(cmd)}")
            
            # Create log files for daemon output
            daemon_log_dir = os.path.join(self.static_cache_path, "logs")
            os.makedirs(daemon_log_dir, exist_ok=True)
            daemon_log_path = os.path.join(daemon_log_dir, f"daemon_{display_id}.log")
            
            # Launch daemon process
            with open(daemon_log_path, 'w') as daemon_log:
                process = subprocess.Popen(
                    cmd,
                    stdout=daemon_log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True  # Detach from parent
                )
            
            # #region agent log
            import json; log_data = {"sessionId": "debug-session", "runId": "initial", "hypothesisId": "daemon", "location": "video_engine.py:launch_daemon:167", "message": "launch_daemon: after Popen", "data": {"pid": process.pid}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
            # #endregion
            
            return process.pid
            
        except Exception as e:
            # #region agent log
            import json; log_data = {"sessionId": "debug-session", "runId": "initial", "hypothesisId": "daemon", "location": "video_engine.py:launch_daemon:175", "message": "launch_daemon: exception", "data": {"exception": str(e), "exception_type": type(e).__name__}, "timestamp": int(__import__('time').time() * 1000)}; open("/Users/shotan/Documents/GitHub/superpaper/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
            # #endregion
            sp_logging.G_LOGGER.error(f"Failed to launch daemon: {e}")
            return None
    
    def get_or_generate_static_frame(self, video_path):
        """
        Get static frame from cache or generate it.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Path to static frame PNG
        """
        # Generate cache filename
        video_name = Path(video_path).stem
        static_path = os.path.join(self.static_cache_path, f"{video_name}.png")
        
        # Return if already exists
        if os.path.exists(static_path):
            sp_logging.G_LOGGER.info(f"Using cached static frame: {static_path}")
            return static_path
        
        # Generate static frame
        sp_logging.G_LOGGER.info(f"Generating static frame for: {video_path}")
        success = self.generate_static_frame(video_path, static_path)
        
        if success:
            return static_path
        else:
            return ""
    
    def generate_static_frame(self, video_path, output_path):
        """
        Generate static frame from video middle point.
        
        Args:
            video_path: Path to video file
            output_path: Path to save PNG
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create asset
            video_url = NSURL.fileURLWithPath_(video_path)
            asset = AVAsset.assetWithURL_(video_url)
            
            # Wait for asset to load
            duration = asset.duration()
            if duration.value == 0:
                sp_logging.G_LOGGER.error("Failed to load video asset")
                return False
            
            # Create image generator
            generator = AVAssetImageGenerator.assetImageGeneratorWithAsset_(asset)
            generator.setAppliesPreferredTrackTransform_(True)
            
            # Get video track for proper sizing
            video_tracks = asset.tracksWithMediaType_("vide")  # AVMediaTypeVideo
            if video_tracks and len(video_tracks) > 0:
                track = video_tracks[0]
                natural_size = track.naturalSize()
                transform = track.preferredTransform()
                
                # Apply transform to get correct orientation
                render_size = CGSizeApplyAffineTransform(natural_size, transform)
                generator.setMaximumSize_((abs(render_size.width), abs(render_size.height)))
            
            # Generate image at midpoint
            duration_seconds = CMTimeGetSeconds(duration)
            midpoint_seconds = duration_seconds / 2.0
            midpoint_time = CMTimeMakeWithSeconds(midpoint_seconds, duration.timescale)
            
            # Generate image synchronously
            error = None
            image_ref, actual_time = generator.copyCGImageAtTime_actualTime_error_(
                midpoint_time,
                None,
                error
            )
            
            if image_ref is None:
                sp_logging.G_LOGGER.error(f"Failed to generate image: {error}")
                return False
            
            # Save image to PNG
            output_url = NSURL.fileURLWithPath_(output_path)
            # Use kUTTypePNG constant or "public.png" string
            destination = CGImageDestinationCreateWithURL(
                output_url,
                "public.png",  # UTI string for PNG
                1,
                None
            )
            
            if destination is None:
                sp_logging.G_LOGGER.error(f"Failed to create image destination for {output_path}")
                return False
            
            CGImageDestinationAddImage(destination, image_ref, None)
            success = CGImageDestinationFinalize(destination)
            
            if success:
                sp_logging.G_LOGGER.info(f"Generated static frame: {output_path}")
                return True
            else:
                sp_logging.G_LOGGER.error("Failed to finalize image")
                return False
                
        except Exception as e:
            sp_logging.G_LOGGER.error(f"Error generating static frame: {e}")
            return False
    
    def kill_all_daemons(self):
        """Kill all running video daemons."""
        # Send terminate notification
        self.send_terminate_notification()
        
        # Kill processes by PID
        for pid in self.daemon_pids:
            try:
                os.kill(pid, signal.SIGTERM)
                sp_logging.G_LOGGER.info(f"Killed daemon PID {pid}")
            except ProcessLookupError:
                pass  # Process already dead
            except Exception as e:
                sp_logging.G_LOGGER.error(f"Error killing PID {pid}: {e}")
        
        # Clear PID list
        self.daemon_pids.clear()
        
        # Don't use killall as it would kill the parent process too
        # The PID-based killing above should be sufficient
    
    def send_terminate_notification(self):
        """Send terminate notification to all daemons."""
        try:
            center = CFNotificationCenterGetDarwinNotifyCenter()
            CFNotificationCenterPostNotification(
                center,
                "com.superpaper.video.terminate",
                None,
                None,
                kCFNotificationDeliverImmediately | kCFNotificationPostToAllSessions
            )
            sp_logging.G_LOGGER.info("Sent terminate notification to daemons")
        except Exception as e:
            sp_logging.G_LOGGER.error(f"Failed to send terminate notification: {e}")
    
    def update_volume(self, new_volume):
        """
        Update volume for all running daemons.
        
        Args:
            new_volume: Float between 0.0 and 1.0
        """
        # Save to UserDefaults
        defaults = NSUserDefaults.standardUserDefaults()
        defaults.setFloat_forKey_(new_volume, "wallpapervolume")
        defaults.synchronize()
        
        # Send notification to daemons
        try:
            center = CFNotificationCenterGetDarwinNotifyCenter()
            CFNotificationCenterPostNotification(
                center,
                "com.superpaper.video.volumeChanged",
                None,
                None,
                kCFNotificationDeliverImmediately | kCFNotificationPostToAllSessions
            )
            sp_logging.G_LOGGER.info(f"Updated volume to {new_volume}")
        except Exception as e:
            sp_logging.G_LOGGER.error(f"Failed to send volume notification: {e}")
    
    def cleanup(self):
        """Cleanup engine resources."""
        self.stop_video_wallpapers()
    
    def stop_video_wallpapers(self):
        """Stop all running video wallpapers."""
        try:
            manager = SPVideoWallpaperManager.sharedManager()
            manager.stopAllWallpapers()
        except Exception as e:
            sp_logging.G_LOGGER.error(f"Error stopping video wallpapers: {e}")
