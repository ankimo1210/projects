using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
using Microsoft.Win32.SafeHandles;

namespace PhotoArchive {
    public sealed class CloudOperation {
        public string Status;
        public int HResult;
        public bool Unsettled;
    }
    public sealed class CloudPolicy {
        public long SyncRootId;
        public ushort HydrationPrimary, HydrationModifiers;
        public uint ProviderStatus;
        public string ProviderName;
    }
    public sealed class CloudFileState {
        public uint Flags;
        public bool InSync;
        public long OnDiskBytes, ValidatedBytes, ModifiedBytes, SyncRootId;
        public uint PinState;
    }
    public static class CloudNative {
        [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
        static extern SafeFileHandle CreateFile(string path,uint access,uint share,IntPtr security,uint creation,uint flags,IntPtr template);
        [DllImport("kernel32.dll",SetLastError=true)]
        static extern bool CancelIoEx(SafeFileHandle handle,IntPtr overlap);
        [DllImport("kernel32.dll",SetLastError=true)]
        static extern bool GetOverlappedResult(SafeFileHandle handle,IntPtr overlap,out uint transferred,bool wait);
        [DllImport("cldapi.dll")]
        static extern int CfHydratePlaceholder(SafeFileHandle file,long offset,long length,uint flags,IntPtr overlap);
        [DllImport("cldapi.dll")]
        static extern int CfSetPinState(SafeFileHandle file,uint state,uint flags,IntPtr overlap);
        [DllImport("cldapi.dll")]
        static extern uint CfGetPlaceholderStateFromAttributeTag(uint attributes,uint tag);
        [DllImport("cldapi.dll")]
        static extern int CfGetPlaceholderInfo(SafeFileHandle file,uint kind,byte[] info,uint size,out uint returned);
        [DllImport("cldapi.dll",CharSet=CharSet.Unicode)]
        static extern int CfGetSyncRootInfoByPath(string path,uint kind,byte[] info,uint size,out uint returned);
        [StructLayout(LayoutKind.Sequential)]
        struct Overlap { public IntPtr Internal,InternalHigh;public uint Offset,OffsetHigh;public IntPtr Event; }
        sealed class PendingIo { public SafeFileHandle File;public EventWaitHandle Event;public IntPtr Pointer; }
        static readonly List<PendingIo> Pending=new List<PendingIo>();
        static SafeFileHandle Open(string path,bool async) {
            var h=CreateFile(path,0x80,7,IntPtr.Zero,3,0x00200000u|(async?0x40000000u:0u),IntPtr.Zero);
            if(h.IsInvalid){h.Dispose();throw new Win32Exception(Marshal.GetLastWin32Error());}return h;
        }
        public static CloudPolicy Policy(string path) {
            byte[] b=new byte[65536];uint n;
            int hr=CfGetSyncRootInfoByPath(path,1,b,(uint)b.Length,out n);
            if(hr<0)Marshal.ThrowExceptionForHR(hr);
            if(n<1056)throw new InvalidOperationException("IncompleteCloudPolicy");
            return new CloudPolicy {SyncRootId=BitConverter.ToInt64(b,0),HydrationPrimary=BitConverter.ToUInt16(b,8),HydrationModifiers=BitConverter.ToUInt16(b,10),ProviderStatus=BitConverter.ToUInt32(b,24),ProviderName=System.Text.Encoding.Unicode.GetString(b,28,512).TrimEnd('\0')};
        }
        public static CloudFileState State(string path,uint attributes,uint tag) {
            uint flags=CfGetPlaceholderStateFromAttributeTag(attributes,tag);
            if(flags==0xffffffff)throw new InvalidOperationException("InvalidCloudState");
            if((flags&1)==0)return new CloudFileState {Flags=flags,InSync=true};
            using(var file=Open(path,false)) {
                byte[] b=new byte[65536];uint n;int hr=CfGetPlaceholderInfo(file,1,b,(uint)b.Length,out n);
                if(hr<0)Marshal.ThrowExceptionForHR(hr);
                if(n<60)throw new InvalidOperationException("IncompleteCloudState");
                return new CloudFileState {Flags=flags,OnDiskBytes=BitConverter.ToInt64(b,0),ValidatedBytes=BitConverter.ToInt64(b,8),ModifiedBytes=BitConverter.ToInt64(b,16),PinState=BitConverter.ToUInt32(b,32),InSync=BitConverter.ToUInt32(b,36)==1,SyncRootId=BitConverter.ToInt64(b,48)};
            }
        }
        static CloudOperation Operate(string path,int timeoutSeconds,bool unpin) {
            if(timeoutSeconds<1||timeoutSeconds>600)throw new ArgumentOutOfRangeException("timeoutSeconds");
            lock(Pending) {
                for(int i=Pending.Count-1;i>=0;i--){if(Pending[i].Event.WaitOne(0)){Pending[i].File.Dispose();Pending[i].Event.Dispose();Marshal.FreeHGlobal(Pending[i].Pointer);Pending.RemoveAt(i);}}
            }
            var watch=Stopwatch.StartNew();var file=Open(path,true);var signal=new EventWaitHandle(false,EventResetMode.ManualReset);
            IntPtr pointer=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(Overlap)));bool retained=false;
            Marshal.StructureToPtr(new Overlap {Event=signal.SafeWaitHandle.DangerousGetHandle()},pointer,false);
            try {
                int hr=unpin?CfSetPinState(file,2,0,pointer):CfHydratePlaceholder(file,0,-1,0,pointer);
                if(hr==0)return new CloudOperation {Status="Available",HResult=0};
                if(hr!=unchecked((int)0x800703e5))return new CloudOperation {Status="Pending",HResult=hr};
                int budget=timeoutSeconds*1000;
                int grace=Math.Min(1000,budget/4);
                int wait=Math.Max(0,budget-grace-(int)watch.ElapsedMilliseconds);
                if(signal.WaitOne(wait)) {
                    uint n;if(GetOverlappedResult(file,pointer,out n,false))return new CloudOperation {Status="Available",HResult=0};
                    return new CloudOperation {Status="Pending",HResult=Marshal.GetHRForLastWin32Error()};
                }
                CancelIoEx(file,pointer);
                int remaining=Math.Max(0,budget-(int)watch.ElapsedMilliseconds);
                if(!signal.WaitOne(remaining)) {
                    file.Dispose();retained=true;
                    lock(Pending){Pending.Add(new PendingIo {File=file,Event=signal,Pointer=pointer});}
                }
                return new CloudOperation {Status="Pending",HResult=unchecked((int)0x800705b4),Unsettled=retained};
            } finally {if(!retained){file.Dispose();signal.Dispose();Marshal.FreeHGlobal(pointer);}}
        }
        public static CloudOperation Hydrate(string path,int seconds){return Operate(path,seconds,false);}
        public static CloudOperation Unpin(string path,int seconds){return Operate(path,seconds,true);}
    }
}
