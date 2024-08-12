package versionManage;

public class PrMamager {
    String prId;
    String title;
    String closedDate;
    String link;
    public PrMamager(String prId, String title, String closedDate, String link) {
        this.prId = prId;
        this.title = title;
        this.closedDate = closedDate;
        this.link = link;
    }

    public String getPrId() {
        return prId;
    }

    public void setPrId(String prId) {
        this.prId = prId;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getClosedDate() {
        return closedDate;
    }

    public void setClosedDate(String closedDate) {
        this.closedDate = closedDate;
    }

    public String getLink() {
        return link;
    }

    public void setLink(String link) {
        this.link = link;
    }
}
