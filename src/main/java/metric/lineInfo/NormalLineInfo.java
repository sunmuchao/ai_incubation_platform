package metric.lineInfo;

public class NormalLineInfo extends LineInfo{
    private LineInfo curTableInfo;
    private LineInfo sonTableInfo;

    public NormalLineInfo(LineInfo curTableInfo, LineInfo sonTableInfo){
        this.curTableInfo = curTableInfo;
        this.sonTableInfo = sonTableInfo;
    }

    public NormalLineInfo(LineInfo curTableInfo){
        this.curTableInfo = curTableInfo;
    }

    public LineInfo getCurTableInfo() {
        return curTableInfo;
    }

    public void setCurTableInfo(LineInfo curTableInfo) {
        this.curTableInfo = curTableInfo;
    }

    public LineInfo getSonTableInfo() {
        if(sonTableInfo == null) {
            sonTableInfo = new LineInfo();
            sonTableInfo.setCols(0);
            sonTableInfo.setRows(0);
        }
        return sonTableInfo;
    }

    public void setSonTableInfo(LineInfo sonTableInfo) {
        this.sonTableInfo = sonTableInfo;
    }
}
