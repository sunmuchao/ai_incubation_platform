package metric.lineInfo;

public class LineInfo {
    private String operate;
    private int Rows;
    private int Cols;
    private int computeTime;
    private int openTime;
    private int time;
    private int point;
    private String lineNumber; //metric对应的行号
    private String[] Fields;
    private String[] groupFields;
    private String[] aggFields;
    private String formula;
    LineInfo(Builder builder){
        this.operate = builder.operate;
        this.Rows = builder.Rows;
        this.Cols = builder.Cols;
        this.computeTime = builder.computeTime;
        this.openTime = builder.openTime;
        this.point = builder.ponit;
        this.time = openTime + computeTime;
        this.lineNumber = builder.lineNumber;
    }

    public LineInfo() {
    }

    public String getFormula() {
        if(formula == null) return "";
        return formula;
    }

    public void setRows(int rows) {
        Rows = rows;
    }

    public void setCols(int cols) {
        Cols = cols;
    }

    public void setFormula(String formula) {
        //将左右"转译
        formula = formula.replaceAll("\"","'");
        this.formula = formula;
    }

    public String[] getGroupFields() {
        return groupFields;
    }

    public void setGroupFields(String[] groupFields) {
        if(groupFields.length == 1 && groupFields[0].trim().equals("")){
            groupFields = new String[0];
        }
        this.groupFields = groupFields;
    }

    public String[] getAggFields() {
        return aggFields;
    }

    public void setAggFields(String[] aggFields) {
        if(aggFields.length == 1 && aggFields[0].trim().equals("")){
            aggFields = new String[0];
        }
        this.aggFields = aggFields;
    }

    public String[] getFields() {
        return Fields;
    }

    public void setFields(String[] fields) {
        Fields = fields;
    }

    public int getPoint() {
        return point;
    }

    public int getComputeTime() {
        return computeTime;
    }

    public void setComputeTime(int computeTime) {
        this.computeTime = computeTime;
    }

    public int getOpenTime() {
        return openTime;
    }

    public String getOperate() {
        return operate;
    }

    public int getRows() {
        return Rows;
    }

    public int getCols() {
        return Cols;
    }

    public void setPoint(int point) {
        this.point = point;
    }

    public void setOpenTime(int openTime) {
        this.openTime = openTime;
    }

    public int getTime() {
        return openTime + computeTime;
    }

    public static class Builder{
        private String operate;
        private int Rows;
        private int Cols;
        private int computeTime;
        private int openTime;
        private int time;
        private String lineNumber; //metric对应的行号

        private int ponit;

        public Builder() {}

        public Builder setOperate(String operate) {
            this.operate = operate;
            return this;
        }

        public Builder setRows(int rows) {
            this.Rows = rows;
            return this;
        }

        public Builder setCols(int cols) {
            this.Cols = cols;
            return this;
        }

        public Builder setComputeTime(int computeTime) {
            this.computeTime = computeTime;
            return this;
        }

        public Builder setTime(int openTime) {
            this.openTime = openTime;
            this.time = openTime + computeTime;
            return this;
        }


        public Builder setPonit(int ponit) {
            this.ponit = ponit;
            return this;
        }

        public Builder setLineNumber(String lineNumber) {
            this.lineNumber = lineNumber;
            return this;
        }

        public LineInfo build() {
            return new LineInfo(this);
        }
    }
}

