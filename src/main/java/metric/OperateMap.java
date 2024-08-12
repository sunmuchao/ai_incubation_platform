package metric;

public class OperateMap {
    private String operate;
    private int pre;
    private int point;

    OperateMap(String operate, int pre){
        this.operate = operate;
        this.pre = pre;
    }

    public String getOperate() {
        return operate;
    }

    public void setOperate(String operate) {
        this.operate = operate;
    }

    public int getPre() {
        return pre;
    }

    public void setPre(int pre) {
        this.pre = pre;
    }

    public int getPoint() {
        return point;
    }

    public void setPoint(int point) {
        this.point = point;
    }
}
