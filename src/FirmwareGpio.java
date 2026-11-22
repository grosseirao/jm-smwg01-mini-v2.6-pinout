import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.util.*;
public class FirmwareGpio extends GhidraScript {
 public void run() throws Exception {
  PrintWriter out=new PrintWriter(getScriptArgs()[0],"UTF-8");
  Set<Function> found=new LinkedHashSet<>();
  long[] targets={0x0e0b6148L,0x0e0b5f28L};
  for(long n:targets){
   Address a=toAddr(n);out.println("TARGET "+a);
   for(Reference r:getReferencesTo(a)){out.println("REF "+r.getFromAddress());Function f=getFunctionContaining(r.getFromAddress());if(f!=null)found.add(f);}
  }
  DecompInterface decomp=new DecompInterface();decomp.openProgram(currentProgram);
  int count=0;
  for(Function f:found){if(count++>=16)break;out.println("FUNCTION "+f.getName()+" "+f.getEntryPoint());DecompileResults d=decomp.decompileFunction(f,20,monitor);if(d.decompileCompleted())out.println(d.getDecompiledFunction().getC());}
  decomp.dispose();out.close();println("GPIO callers="+found.size());
 }
}
