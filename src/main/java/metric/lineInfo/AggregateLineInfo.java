package metric.lineInfo;

public class AggregateLineInfo extends LineInfo{
    private LineInfo curTableInfo;
    private LineInfo sonTableInfo;

    public AggregateLineInfo(LineInfo curTableInfo, LineInfo sonTableInfo){
        this.curTableInfo = curTableInfo;
        this.sonTableInfo = sonTableInfo;
    }

    public LineInfo getCurTableInfo() {
        return curTableInfo;
    }

    public void setCurTableInfo(LineInfo curTableInfo) {
        this.curTableInfo = curTableInfo;
    }

    public LineInfo getSonTableInfo() {
        return sonTableInfo;
    }

    public void setSonTableInfo(LineInfo sonTableInfo) {
        this.sonTableInfo = sonTableInfo;
    }
}
