package metric.lineInfo;

import java.util.ArrayList;

public class UnionLineInfo extends LineInfo{
    private LineInfo curTableInfo;
    private ArrayList<LineInfo> sonTableInfos;
    public UnionLineInfo(LineInfo curTableInfo){
        this.curTableInfo = curTableInfo;
    }

    public LineInfo getCurTableInfo() {
        return curTableInfo;
    }

    public void setCurTableInfo(LineInfo curTableInfo) {
        this.curTableInfo = curTableInfo;
    }

    public ArrayList<LineInfo> getSonTableInfos() {
        return sonTableInfos;
    }

    public void addSonTableInfos(ArrayList<LineInfo> sonTableInfos) {
        this.sonTableInfos = sonTableInfos;
    }
}
