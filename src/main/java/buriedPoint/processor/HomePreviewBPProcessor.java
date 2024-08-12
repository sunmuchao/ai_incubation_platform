package buriedPoint.processor;

import buriedPoint.DBUtils;
import buriedPoint.point.BuriedPoint;

public class HomePreviewBPProcessor extends BPProcessor {
    public HomePreviewBPProcessor(BuriedPoint buriedPoint, DBUtils dbUtils, String traceid, String cookie) {
        super(buriedPoint, dbUtils, traceid, cookie);
    }

    public void process() {
        System.out.println("主页预览暂时不处理");
    }
}
