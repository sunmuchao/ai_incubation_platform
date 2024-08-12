package metric.lineInfo;

public class FilterLineInfo  extends LineInfo{
    private LineInfo curTableInfo;
    private LineInfo sonTableInfo;

    public FilterLineInfo(LineInfo curTableInfo, LineInfo sonTableInfo){
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
