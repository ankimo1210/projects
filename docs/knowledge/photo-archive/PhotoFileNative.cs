using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
using System.Text;
using System.Security.Cryptography;

namespace PhotoArchive {
    public sealed class NativeVolume {
        public string NativeId;
        public long FreeBytes,ClusterBytes;
        public string FileSystem;
    }
    public static class FileMetadata {
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        static extern SafeFileHandle CreateFile(string path, uint access, uint share, IntPtr security, uint creation, uint flags, IntPtr template);
        [DllImport("kernel32.dll", SetLastError=true)]
        static extern bool DeviceIoControl(SafeFileHandle file, uint code, IntPtr input, uint inputSize, byte[] output, uint outputSize, out uint returned, IntPtr overlapped);
        [DllImport("kernel32.dll", SetLastError=true)]
        static extern bool GetFileInformationByHandle(SafeFileHandle file, out FileInfo info);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        static extern bool GetVolumeNameForVolumeMountPoint(string root,StringBuilder name,uint size);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        static extern bool GetDiskFreeSpaceEx(string root,out ulong available,out ulong total,out ulong free);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        static extern bool GetDiskFreeSpace(string root,out uint sectors,out uint bytes,out uint freeClusters,out uint totalClusters);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        static extern bool GetVolumeInformation(string root,StringBuilder label,uint labelSize,out uint serial,out uint maxComponent,out uint flags,StringBuilder fs,uint fsSize);
        [DllImport("kernel32.dll", EntryPoint="DeviceIoControl", SetLastError=true)]
        static extern bool QueryDevice(SafeFileHandle file,uint code,byte[] input,uint inputSize,byte[] output,uint outputSize,out uint returned,IntPtr overlap);
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
        public static NativeVolume Volume(string root) {
            var guid=new StringBuilder(1024);var label=new StringBuilder(256);var fs=new StringBuilder(64);
            ulong available,total,free;uint sectors,bytes,freeClusters,totalClusters,serial,maxComponent,flags;
            if(!GetVolumeNameForVolumeMountPoint(root,guid,(uint)guid.Capacity)||!GetDiskFreeSpaceEx(root,out available,out total,out free)||!GetDiskFreeSpace(root,out sectors,out bytes,out freeClusters,out totalClusters)||!GetVolumeInformation(root,label,(uint)label.Capacity,out serial,out maxComponent,out flags,fs,(uint)fs.Capacity))throw new Win32Exception(Marshal.GetLastWin32Error());
            string deviceHash=null;
            using(var h=CreateFile("\\\\.\\"+root.Substring(0,2),0,7,IntPtr.Zero,3,0,IntPtr.Zero)) {
                if(h.IsInvalid)throw new Win32Exception(Marshal.GetLastWin32Error());
                byte[] input=new byte[12];input[0]=3;byte[] output=new byte[65536];uint n;
                if(QueryDevice(h,0x2D1400,input,(uint)input.Length,output,(uint)output.Length,out n,IntPtr.Zero)&&n>=20) {
                    using(var sha=SHA256.Create()){deviceHash=BitConverter.ToString(sha.ComputeHash(output,0,(int)n)).Replace("-","");}
                } else {
                    input[0]=2;
                    if(QueryDevice(h,0x2D1400,input,(uint)input.Length,output,(uint)output.Length,out n,IntPtr.Zero)&&n>=12&&BitConverter.ToUInt32(output,8)>0) {
                        using(var sha=SHA256.Create()){deviceHash=BitConverter.ToString(sha.ComputeHash(output,0,(int)n)).Replace("-","");}
                    }
                }
            }
            if(deviceHash==null)throw new InvalidOperationException("NativePhysicalIdentityUnavailable");
            return new NativeVolume {NativeId=guid.ToString()+"|"+serial.ToString("X8")+"|"+deviceHash,FreeBytes=(long)available,ClusterBytes=(long)sectors*bytes,FileSystem=fs.ToString()};
        }
    }
}
