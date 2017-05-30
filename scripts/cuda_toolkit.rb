cask 'cuda_toolkit' do
  version '8.0.61'
  sha256 '8a47dd19108c1f5ddb0f3bf6a23d5ad29598e5985eee8bebe2febd91b2796ee9'

  url "https://developer.nvidia.com/compute/cuda/#{version.major_minor}/Prod2/network_installers/cuda_#{version}_mac_network-dmg"
  name 'Nvidia CUDA'
  homepage 'https://developer.nvidia.com/cuda-zone'

  installer script: {
                      executable: 'CUDAMacOSXInstaller.app/Contents/MacOS/CUDAMacOSXInstaller',
                      args:       ['--accept-eula', '--silent', '--no-window', '--install-package=cuda-toolkit'],
                    }

  uninstall script:    {
                         executable: "/Developer/NVIDIA/CUDA-#{version.major_minor}/bin/uninstall_cuda_#{version.major_minor}.pl",
                         sudo:       true,
                       },
            launchctl: [
                         'com.nvidia.CUDASoftwareUpdate',
                         'com.nvidia.cuda.launcher',
                         'com.nvidia.cudad',
                       ],
            kext:      'com.nvidia.CUDA',
            delete:    '/Library/PreferencePanes/CUDA Preferences.prefPane'

  zap delete: '/Library/Frameworks/CUDA.framework'
end
