
package buriedPoint;

import buriedPoint.point.BuriedPoint;
import buriedPoint.processor.*;

public class BPProcessorFactory {
    private DBUtils dbUtils;
    private String traceid;
    private BuriedPoint buriedPoint;
    private String cookie;
    BPProcessorFactory(BuriedPoint buriedPoint, DBUtils dbUtils, String traceid, String cookie) {
        this.buriedPoint = buriedPoint;
        this.dbUtils = dbUtils;
        this.traceid = traceid;
        this.cookie = cookie;
    }

    BPProcessor bpProcessor;
    public BPProcessor createProcessor(){
        if(buriedPoint.getClass().getName().contains("OperatorsPageBuriedPoint")){
            bpProcessor = new OperatorsPageBPProcessor(buriedPoint,dbUtils,traceid,cookie);
            //System.out.println("OperatorsPageBuriedPoint");
        }else if(buriedPoint.getClass().getName().contains("HomePreviewBuriedPoint")){
            //System.out.println("HomePreviewBuriedPoint");
            bpProcessor = new HomePreviewBPProcessor(buriedPoint,dbUtils,traceid,cookie);
        }else if(buriedPoint.getClass().getName().contains("EditChartBuriedPoint")){
            //System.out.println("EditChartBuriedPoint");
            bpProcessor = new EditChartBPProcessor(buriedPoint,dbUtils,traceid,cookie);
        }else if(buriedPoint.getClass().getName().contains("UpdateBuriedPoint")){
            //System.out.println("UpdateBuriedPoint");
            bpProcessor = new UpdateBPProcessor(buriedPoint,dbUtils,traceid,cookie);
        }else if(buriedPoint.getClass().getName().contains("WidgetDataBuriedPoint")){
            //System.out.println("UpdateBuriedPoint");
            //走预览逻辑
            bpProcessor = new OperatorsPageBPProcessor(buriedPoint,dbUtils,traceid,cookie);
        }else if(buriedPoint.getClass().getName().contains("PreviewChartBuriedPoint")){
            //走预览逻辑
            bpProcessor = new OperatorsPageBPProcessor(buriedPoint,dbUtils,traceid,cookie);
        } else if(buriedPoint.getClass().getName().contains("LinkageRowsBuriedPoint")){
            //走预览逻辑
            bpProcessor = new OperatorsPageBPProcessor(buriedPoint,dbUtils,traceid,cookie);
        } else if(buriedPoint.getClass().getName().contains("FilterBuriedPoint")){
            //走预览逻辑
            bpProcessor = new OperatorsPageBPProcessor(buriedPoint,dbUtils,traceid,cookie);
        } else if(buriedPoint.getClass().getName().contains("JoinStepDetailBuriedPoint")){
            //走预览逻辑
            bpProcessor = new OperatorsPageBPProcessor(buriedPoint,dbUtils,traceid,cookie);
        }

        return bpProcessor;
    }
}

