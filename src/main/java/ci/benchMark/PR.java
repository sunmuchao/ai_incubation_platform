package ci.benchMark;

public class PR {
    private String displayId;
    private String builder;
    private String prId;
    private PRTask prTask;
    private Long updatedDatelong;
    private String state;
    private Long lastestAddOrReMoveReviewerTime = 0L;
    private Long oldestCreatedDate = Long.MAX_VALUE;
    private Long closedDate;
    private Boolean isLLVM = false;
    //是否只有九数云模块的改动
    private Boolean isOnlyHihidataChange = false;
    //是否包含bi模块的改动
    private Boolean isContainBIChange = false;
    //是否包含Hihidata模块的改动
    private Boolean isContainHihidataChange = false;
    private String codeType;

    //触发的次数信息统计
    private int runCount = 0;
    private int benchmarkDictCount = 0;
    private int benchmarkNormalCount = 0;
    private int runLlvmCount = 0;
    private int benchmarkllvmNormalCount = 0;


    public PR(String displayId, String builder, String prId) {
        this.displayId = displayId;
        this.builder = builder;
        this.prId = prId;
    }

    public PR(String displayId, String prId) {
        this.displayId = displayId;
        this.prId = prId;
    }

    public int getRunCount() {
        return runCount;
    }

    public void addRunCount(int count) {
        this.runCount += count;
    }

    public String getCodeType() throws Exception {
        if (codeType != null) {
            return codeType;
        } else {
            throw new Exception("codeType is null");
        }
    }

    public PR setCodeType(String codeType) {
        this.codeType = codeType;
        return this;
    }

    public int getBenchmarkDictCount() {
        return benchmarkDictCount;
    }

    public void addBenchmarkDictCount(int count) {
        this.benchmarkDictCount += count;
    }

    public int getBenchmarkNormalCount() {
        return benchmarkNormalCount;
    }

    public void addBenchmarkNormalCount(int count) {
        this.benchmarkNormalCount += count;
    }

    public int getRunLlvmCount() {
        return runLlvmCount;
    }

    public void addRunLlvmCount(int count) {
        this.runLlvmCount += count;
    }

    public int getBenchmarkllvmNormalCount() {
        return benchmarkllvmNormalCount;
    }

    public void addBenchmarkllvmNormalCount(int count) {
        this.benchmarkllvmNormalCount += count;
    }

    public Boolean getLLVM() {
        return isLLVM;
    }

    public void setLLVM(Boolean LLVM) {
        System.out.println("是否是c++代码：" + LLVM);
        isLLVM = LLVM;
    }

    public Boolean getIsOnlyHihidataChange() {
        return isOnlyHihidataChange;
    }

    public void setIsOnlyHihidataChange(Boolean onlyHihidataChange) {
        System.out.println("是否仅有Hihidata模块改动：" + onlyHihidataChange);
        isOnlyHihidataChange = onlyHihidataChange;
    }

    public Boolean getIsContainBIChange() {
        return isContainBIChange;
    }

    public void setIsContainBIChange(Boolean isContainBIChange) {
        System.out.println("是否包含BI模块改动：" + isContainBIChange);
        this.isContainBIChange = isContainBIChange;
    }

    public Boolean getIsContainHihidataChange() {
        return isContainHihidataChange;
    }

    public void setIsContainHihidataChange(Boolean isContainHihidataChange) {
        System.out.println("是否包含Hihidata模块改动：" + isContainHihidataChange);
        this.isContainHihidataChange = isContainHihidataChange;
    }



    public Long getClosedDate() {
        return closedDate;
    }

    public void setClosedDate(Long closedDate) {
        this.closedDate = closedDate;
    }

    public Long getOldestCreatedDate() {
        return oldestCreatedDate;
    }

    public void setOldestCreatedDate(Long createdDate) {
        oldestCreatedDate = Math.min(createdDate, oldestCreatedDate);
    }

    public String getState() {
        return state;
    }

    public void setState(String state) {
        this.state = state;
    }

    public Long getLastestAddOrReMoveReviewerTime() {
        return lastestAddOrReMoveReviewerTime / 1000;
    }

    public void setLastestAddOrReMoveReviewerTime(Long addOrReMoveReviewerTime) {
        this.lastestAddOrReMoveReviewerTime = Math.max(addOrReMoveReviewerTime, lastestAddOrReMoveReviewerTime);
    }

    public Long getUpdatedDatelong() {
        return updatedDatelong;
    }

    public void setUpdatedDatelong(String updatedDate) {
        long updatedDatelong = Long.parseLong(updatedDate.substring(0, updatedDate.length() - 3));
        this.updatedDatelong = updatedDatelong;
    }

    public String getDisplayId() {
        return displayId;
    }

    public String getBuilder() {
        return builder;
    }

    public String getPrId() throws Exception {
        if (prId != null) {
            return prId;
        } else {
            throw new Exception("prId is null");
        }
    }

    public PRTask getTask() {
        return prTask;
    }

    public void buildTask(String testType, String[] dataTypes, String[] codeTypes) {
        prTask = new PRTask(testType, dataTypes, codeTypes);
    }

    public class PRTask {
        private String testType;
        private String[] dataTypes;
        private String[] codeTypes;

        PRTask(String testType, String[] dataTypes, String[] codeTypes) {
            this.testType = testType;
            this.dataTypes = dataTypes;
            this.codeTypes = codeTypes;
        }


        public String getTestType() {
            return testType;
        }

        public String[] getDataTypes() {
            return dataTypes;
        }

        public void setTestType(String testType) {
            this.testType = testType;
        }

        public void setDataTypes(String[] dataTypes) {
            this.dataTypes = dataTypes;
        }

        public String[] getCodeTypes() {
            return codeTypes;
        }

        public void setCodeTypes(String[] codeTypes) {
            this.codeTypes = codeTypes;
        }
    }
}
