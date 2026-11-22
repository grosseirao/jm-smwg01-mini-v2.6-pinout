import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.lang.Register;
import java.math.BigInteger;
public class FirmwareSetup extends GhidraScript {
 public void run() throws Exception {
  Register t=currentProgram.getRegister("TMode");
  currentProgram.getProgramContext().setValue(t,currentProgram.getMinAddress(),currentProgram.getMaxAddress(),BigInteger.ONE);
  long[] starts={0x0e008060L,0x0e02e080L,0x0e02e100L};
  for(long n:starts){Address a=toAddr(n); disassemble(a); if(getFunctionAt(a)==null) createFunction(a,null);}
 }
}
