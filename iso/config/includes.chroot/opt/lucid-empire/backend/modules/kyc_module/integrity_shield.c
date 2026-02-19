/*
 * LUCID TITAN KYC MODULE :: INTEGRITY SHIELD
 * Authority: Dva.12 | Status: TITAN_ACTIVE
 * Purpose: Source-level patches for Chromium/Firefox to spoof device enumeration and capabilities.
 * 
 * Target File: media/capture/video/fake_video_capture_device_factory.cc
 * Function: FakeVideoCaptureDeviceFactory::GetDevicesInfo
 * 
 * Reference: Section 3.1.2 - Chromium Source-Level Modification
 */

// NOTE: This file is a patch artifact. It must be applied to the Chromium source tree 
// before compiling the browser build used in the ISO.

#include "media/capture/video/fake_video_capture_device_factory.h"
#include "media/capture/video/video_capture_device_descriptor.h"

namespace media {

// ORIGINAL IMPLEMENTATION (Detected):
// void FakeVideoCaptureDeviceFactory::GetDevicesInfo(
//     const GetDevicesInfoCallback& callback) {
//   std::vector<VideoCaptureDeviceInfo> devices_info;
//   devices_info.emplace_back(
//       VideoCaptureDeviceDescriptor("Fake Device 1", "0",
//                                    VideoCaptureApi::UNKNOWN_PLATFORM),
//       VideoCaptureFormats());
//   ...
// }

// LUCID TITAN PATCHED IMPLEMENTATION:
void FakeVideoCaptureDeviceFactory::GetDevicesInfo(
    const GetDevicesInfoCallback& callback) {
  
  std::vector<VideoCaptureDeviceInfo> devices_info;

  // Spoofing the Device Label
  // "Facetime HD Camera" or "Logitech C920" are high-trust hardware strings.
  // Avoid "Virtual", "Fake", or "OBS".
  
  // Device 1: Integrated Webcam
  devices_info.emplace_back(
      VideoCaptureDeviceDescriptor(
          "Facetime HD Camera (Built-in)",   // Display Name
          "/dev/video0",                     // Device ID (mapped to v4l2loopback)
          VideoCaptureApi::LINUX_V4L2_SINGLE_PLANE
      ),
      VideoCaptureFormats() // Auto-negotiate formats
  );

  // Device 2: External High-Res Camera (optional)
  devices_info.emplace_back(
      VideoCaptureDeviceDescriptor(
          "Logitech HD Pro Webcam C920",     // Display Name
          "/dev/video2",                     // Device ID
          VideoCaptureApi::LINUX_V4L2_SINGLE_PLANE
      ),
      VideoCaptureFormats()
  );

  // LOGGING: confirm injection
  // DLOG(INFO) << "LUCID TITAN: Injected " << devices_info.size() << " synthetic devices.";

  callback.Run(std::move(devices_info));
}

}  // namespace media

/*
 * BUILD INSTRUCTIONS:
 * 1. Copy this logic into chromium/src/media/capture/video/fake_video_capture_device_factory.cc
 * 2. Build Chromium with:
 *    gn gen out/Release --args="is_debug=false enable_nacl=false"
 *    autoninja -C out/Release chrome
 */
