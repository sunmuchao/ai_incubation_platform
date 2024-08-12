package ci.benchMark;

public class ResultDao {
    boolean isTrue;
    String detail;

    public ResultDao() {
    }

    public ResultDao(boolean isTrue, String detail) {
        this.isTrue = isTrue;
        this.detail = detail;
    }

    public boolean isTrue() {
        return isTrue;
    }

    public void setTrue(boolean aTrue) {
        isTrue = aTrue;
    }

    public String getDetail() {
        return detail;
    }

    public void setDetail(String detail) {
        this.detail = detail;
    }
}
