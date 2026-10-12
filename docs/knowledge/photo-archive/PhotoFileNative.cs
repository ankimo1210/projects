using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

namespace PhotoArchive {
    public static class FileMetadata {
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        static extern SafeFileHandle CreateFile(string path, uint access, uint share, IntPtr security, uint creation, uint flags, IntPtr template);
        [DllImport("kernel32.dll", SetLastError=true)]
        static extern bool DeviceIoControl(SafeFileHandle file, uint code, IntPtr input, uint inputSize, byte[] output, uint outputSize, out uint returned, IntPtr overlapped);
        [DllImport("kernel32.dll", SetLastError=true)]
        static extern bool GetFileInformationByHandle(SafeFileHandle file, out FileInfo info);
        [StructLayout(LayoutKind.Sequential)]
        struct FileInfo {
            public uint Attributes, CreationLow, CreationHigh, AccessLow, AccessHigh, WriteLow, WriteHigh, VolumeSerial, SizeHigh, SizeLow, Links, IndexHigh, IndexLow;
        }
        static SafeFileHandle Open(string path) {
            var handle=CreateFile(path, 0x80, 7, IntPtr.Zero, 3, 0x02200000, IntPtr.Zero);
            if(handle.IsInvalid) { handle.Dispose();throw new Win32Exception(Marshal.GetLastWin32Error()); }
            return handle;
        }
        public static uint ReparseTag(string path) {
            using(var h=Open(path)) {
                byte[] bytes=new byte[16384];uint returned;
                if(!DeviceIoControl(h,0x900A8,IntPtr.Zero,0,bytes,(uint)bytes.Length,out returned,IntPtr.Zero)) throw new Win32Exception(Marshal.GetLastWin32Error());
                if(returned<8) throw new InvalidOperationException("InvalidReparseData");
                return BitConverter.ToUInt32(bytes,0);
            }
        }
        public static string Identity(string path) {
            using(var h=Open(path)) {
                FileInfo info;
                if(!GetFileInformationByHandle(h,out info)) throw new Win32Exception(Marshal.GetLastWin32Error());
                return info.VolumeSerial.ToString("X8")+":"+info.IndexHigh.ToString("X8")+info.IndexLow.ToString("X8");
            }
        }
    }
}
