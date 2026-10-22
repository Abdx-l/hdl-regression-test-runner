module and_gate_tb;
reg a, b;
wire y;
and_gate dut(a,b,y);
initial begin
  a=0; b=0; #1; if (y !== 0) $fatal(1,"FAIL: 0 and 0");
  a=1; b=1; #1; if (y !== 1) $fatal(1,"FAIL: 1 and 1");
  $display("PASS"); $finish;
end
endmodule

