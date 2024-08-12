package buriedPoint.executor;

import java.util.ArrayList;

public class DataFlowExecutor extends Executor{
    private String DataFlowExecutorId;
    private int txnWriteTime;
    private int DataFlowExecutorTime;

    private int calculationTime;

    private int ChecksumImportDataBracketTime;

    public DataFlowExecutor(String DataFlowExecutorId, int DataFlowExecutorTime){
        this.DataFlowExecutorId = DataFlowExecutorId;
        this.DataFlowExecutorTime = DataFlowExecutorTime;
        childIds = new ArrayList();
    }

    public int getCalculationTime() {
        return calculationTime;
    }

    public void setCalculationTime(int calculationTime) {
        this.calculationTime = calculationTime;
    }

    public int getChecksumImportDataBracketTime() {
        return ChecksumImportDataBracketTime;
    }

    public void setChecksumImportDataBracketTime(int checksumImportDataBracketTime) {
        ChecksumImportDataBracketTime = checksumImportDataBracketTime;
    }

    public String getDataFlowExecutorId() {
        return DataFlowExecutorId;
    }

    public void setDataFlowExecutorId(String dataFlowExecutorId) {
        DataFlowExecutorId = dataFlowExecutorId;
    }

    public int getTxnWriteTime() {
        return txnWriteTime;
    }

    public void setTxnWriteTime(int txnWriteTime) {
        this.txnWriteTime = txnWriteTime;
    }

    public int getDataFlowExecutorTime() {
        return DataFlowExecutorTime;
    }

    public void setDataFlowExecutorTime(int dataFlowExecutorTime) {
        DataFlowExecutorTime = dataFlowExecutorTime;
    }
}
