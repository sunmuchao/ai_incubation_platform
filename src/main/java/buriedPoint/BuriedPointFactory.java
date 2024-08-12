package buriedPoint;

import buriedPoint.point.*;

public class BuriedPointFactory {
    public BuriedPoint createBuriedPoint(String kind,String traceid){
        BuriedPoint buriedPoint = null;
        if (kind.equals("homepreview")) {
            //主页预览的根span
            System.out.println("当前埋点类型: 主页预览的根span");
            buriedPoint = new HomePreviewBuriedPoint(traceid);
        } else if (kind.equals("update")) {
            //更新
            System.out.println("当前埋点类型: 更新");
            buriedPoint = new UpdateBuriedPoint(traceid);
        } else if (kind.equals("operatorspage")) {
            //查询
            System.out.println("当前埋点类型: 查询");
            buriedPoint = new OperatorsPageBuriedPoint(traceid);
        } else if(kind.equals("editchart")){
            //编辑图表
            System.out.println("当前埋点类型: 编辑图表");
            buriedPoint = new EditChartBuriedPoint(traceid);
        } else if(kind.equals("widgetdata")){
            //查询图表组件的前100行数据，带总行数
            System.out.println("当前埋点类型: 查询图表组件的前100行数据");
            buriedPoint = new WidgetDataBuriedPoint(traceid);
        }else if(kind.equals("linkagerows")){
            //查询图表组件的前100行数据，带总行数
            System.out.println("当前埋点类型: 发起联动，获取行号");
            buriedPoint = new LinkageRowsBuriedPoint(traceid);
        }else if(kind.equals("previewchart")){
            //预览图表
            System.out.println("当前埋点类型: 预览图表");
            buriedPoint = new PreviewChartBuriedPoint(traceid);
        }else if(kind.equals("filter.getstringvalues")){
            //预览图表
            System.out.println("当前埋点类型: 过滤器");
            buriedPoint = new FilterBuriedPoint(traceid);
        }else if(kind.equals("join.stepDetail")){
            //预览图表
            System.out.println("当前埋点类型: 左右合并--合并明细--查看上一步明细");
            buriedPoint = new JoinStepDetailBuriedPoint(traceid);
        } else{
            //非已知埋点，先走查询逻辑
            System.out.println("当前埋点类型: 非已知埋点");
            buriedPoint = new OperatorsPageBuriedPoint(traceid);
        }

        return buriedPoint;
    }
}
