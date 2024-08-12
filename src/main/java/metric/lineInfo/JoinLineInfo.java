package metric.lineInfo;

public class JoinLineInfo  extends LineInfo{
    private LineInfo curTableInfo;
    private LineInfo leftTableInfo;
    private LineInfo rightTableInfo;
    public JoinLineInfo(LineInfo curTableInfo, LineInfo leftTableInfo, LineInfo rightTableInfo) {
        this.curTableInfo = curTableInfo;
        this.leftTableInfo = leftTableInfo;
        this.rightTableInfo = rightTableInfo;
    }

    public LineInfo getCurTableInfo() {
        return curTableInfo;
    }

    public void setCurTableInfo(LineInfo curTableInfo) {
        this.curTableInfo = curTableInfo;
    }

    public LineInfo getLeftTableInfo() {
        return leftTableInfo;
    }

    public void setLeftTableInfo(LineInfo leftTableInfo) {
        this.leftTableInfo = leftTableInfo;
    }

    public LineInfo getRightTableInfo() {
        return rightTableInfo;
    }

    public void setRightTableInfo(LineInfo rightTableInfo) {
        this.rightTableInfo = rightTableInfo;
    }
}
