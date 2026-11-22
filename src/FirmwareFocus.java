import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.util.*;
public class FirmwareFocus extends GhidraScript {
 public void run() throws Exception {
  PrintWriter out=new PrintWriter(getScriptArgs()[0],"UTF-8");
  DecompInterface decomp=new DecompInterface(); decomp.openProgram(currentProgram);
  Set<Function> found=new LinkedHashSet<>();
  long[] targets={0x0e0ca978L,0x0e0ca954L,0x0e0ca9acL,0x0e02e19cL,0x0e0fe898L};
  for(long n:targets){
   Address a=toAddr(n);out.println("TARGET "+a);
   for(Reference r:getReferencesTo(a)){
    out.println("REF "+r.getFromAddress()+" "+r.getReferenceType());
    Function f=getFunctionContaining(r.getFromAddress());if(f!=null)found.add(f);
    if(f==null)for(Reference rr:getReferencesTo(r.getFromAddress())){Function g=getFunctionContaining(rr.getFromAddress());if(g!=null)found.add(g);}
   }
  }
  for(Function f:found){out.println("FUNCTION "+f.getName()+" "+f.getEntryPoint());DecompileResults d=decomp.decompileFunction(f,30,monitor);if(d.decompileCompleted())out.println(d.getDecompiledFunction().getC());else out.println(d.getErrorMessage());}
  out.close();decomp.dispose();println("Focused report saved; functions="+found.size());
 }
}
