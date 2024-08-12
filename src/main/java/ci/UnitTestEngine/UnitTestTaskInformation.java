package ci.UnitTestEngine;

import com.moandjiezana.toml.Toml;
import com.moandjiezana.toml.TomlWriter;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * @author sunmuchao
 * @date 2024/8/7 5:46 下午
 */
public class UnitTestTaskInformation {
    private String uuid;
    private String prId;
    private boolean isContainBIChange;
    private boolean isContainHihidataChange;
    private int documentNumber;
    private List<String> operatorNodeNames;
    private String builder;
    private String branch;

    UnitTestTaskInformation(String uuid, String prId){
        this.uuid = uuid;
        this.prId = prId;
        operatorNodeNames = new ArrayList<>();
    }

    public String getBranch() {
        return branch;
    }

    public UnitTestTaskInformation setBranch(String branch) {
        this.branch = branch;
        return this;
    }

    public String getBuilder() {
        return builder;
    }

    public UnitTestTaskInformation setBuilder(String builder) {
        this.builder = builder;
        return this;
    }

    public UnitTestTaskInformation addOperatorNodeName(String operatorNodeName){
        operatorNodeNames.add(operatorNodeName);
        return this;
    }

    public List<String> getOperatorNodeNames(){
        return operatorNodeNames;
    }

    public int getDocumentNumber() {
        return documentNumber;
    }

    public UnitTestTaskInformation setDocumentNumber(int documentNumber) {
        this.documentNumber = documentNumber;
        return this;
    }

    public String getUuid() {
        return uuid;
    }

    public String getPrId() {
        return prId;
    }

    public boolean isContainBIChange() {
        return isContainBIChange;
    }

    public boolean isContainHihidataChange() {
        return isContainHihidataChange;
    }

    public UnitTestTaskInformation setContainBIChange(boolean containBIChange) {
        isContainBIChange = containBIChange;
        return this;
    }

    public UnitTestTaskInformation setContainHihidataChange(boolean containHihidataChange) {
        isContainHihidataChange = containHihidataChange;
        return this;
    }

    public void generateTomlFile(String filePath) {
        Map<String, Object> tomlMap = new HashMap<>();
        tomlMap.put("uuid", this.uuid);
        tomlMap.put("prId", this.prId);
        tomlMap.put("isContainBIChange", this.isContainBIChange);
        tomlMap.put("isContainHihidataChange", this.isContainHihidataChange);
        tomlMap.put("documentNumber", this.documentNumber);
        tomlMap.put("builder", this.builder);
        tomlMap.put("branch", this.branch);
        //tomlMap.put("operatorNodeNames", this.operatorNodeNames);

        TomlWriter writer = new TomlWriter();
        String tomlString = writer.write(tomlMap);
        try (FileWriter fileWriter = new FileWriter(filePath)) {
            fileWriter.write(tomlString);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public static UnitTestTaskInformation fromTomlFile(String filePath) {
        Toml toml = new Toml().read(new File(filePath));

        String uuid = toml.getString("uuid");
        String prId = toml.getString("prId");
        boolean isContainBIChange = toml.getBoolean("isContainBIChange");
        boolean isContainHihidataChange = toml.getBoolean("isContainHihidataChange");
        int documentNumber = toml.getLong("documentNumber").intValue();
        String builder = toml.getString("builder");
        String branch = toml.getString("branch");

        UnitTestTaskInformation taskInfo = new UnitTestTaskInformation(uuid, prId)
                .setContainBIChange(isContainBIChange)
                .setContainHihidataChange(isContainHihidataChange)
                .setDocumentNumber(documentNumber)
                .setBuilder(builder)
                .setBranch(branch);


        return taskInfo;
    }
}
