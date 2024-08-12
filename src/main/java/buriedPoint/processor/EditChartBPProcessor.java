package buriedPoint.processor;

import buriedPoint.DBUtils;
import buriedPoint.point.BuriedPoint;

public class EditChartBPProcessor extends BPProcessor {

    public EditChartBPProcessor(BuriedPoint buriedPoint, DBUtils dbUtils, String traceid, String cookie) {
        super(buriedPoint, dbUtils, traceid, cookie);
    }

    public void process() {
        System.out.println("编辑图表暂时不处理");
    }
}
