/*
package updateBlood;

import cn.hutool.core.lang.Assert;
import com.google.common.graph.ElementOrder;
import com.google.common.graph.GraphBuilder;
import com.google.common.graph.MutableGraph;
import com.opencsv.CSVReader;
import updateBlood.PathContent.RootPath;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InterruptedIOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;

public class GraphUtils {
    private MutableGraph<String> graph;
    //记录的是当前节点的每条血缘路径上的节点数
    public Map<String, Integer> successorNodes = new HashMap();
    //记录经过的前驱节点
    public Set<String> predecessorNodeSet;
    public Map<String, MutableGraph<String>> updateNetworks;
    //private BufferedWriter bufferedWriter;
    private String dagIdPath;
    private Map<String, Integer> csvMapping;
    GraphUtils(String dagIdPath, Map<String, Integer> csvMapping) throws IOException {
        this.dagIdPath = dagIdPath;
        this.predecessorNodeSet = new HashSet<>();
        this.updateNetworks = new HashMap();
        this.csvMapping = csvMapping;
        createAllGraphs();
        //bufferedWriter = new BufferedWriter(new FileWriter(dagIdPath + "test.txt"));
    }

    private void createAllGraphs() throws IOException {
        //遍历所有的csv文件
        File directory = new File(dagIdPath);
        File[] files = directory.listFiles();
        for (File file : files) {
            String fileName = file.getName();
            createGraph(fileName);
        }
    }

    private void createGraph(String fileName) throws IOException {
        List<String[]> list = new ArrayList<>();
        String dagid = fileName.split("\\.")[0];
        if (updateNetworks.containsKey(dagid)) {
            graph = updateNetworks.get(dagid);
        } else {
            graph = GraphBuilder.directed() //指定为有向图
                    .nodeOrder(ElementOrder.<String>insertion()) //节点按插入顺序输出
                    .allowsSelfLoops(false) //允许自环
                    .build();
            updateNetworks.put(dagid, graph);
        }

        CSVReader csvReader = new CSVReader(Files.newBufferedReader(Paths.get(dagIdPath + fileName)));
        String[] fields;
        //先放入内存中进行加速
        while ((fields = csvReader.readNext()) != null) {
            list.add(fields);
        }

        for(String[] fields2 : list){
            String[] preTableIds = fields2[csvMapping.get("preTableIds")].split(",");
            String curTableId = fields2[csvMapping.get("tableId")] + "_" + fields2[csvMapping.get("dataModify")];
            for (String preTableId : preTableIds) {
                if (!preTableId.equals("")) {
                    //寻找preTableId的dataModify
                    for(String[] fields3 : list){
                        if (fields3[csvMapping.get("tableId")].contains(preTableId)) {
                            String dataModify = fields3[csvMapping.get("dataModify")];
                            preTableId = preTableId + "_" + dataModify;
                            break;
                        }
                    }
                    graph.putEdge(preTableId, curTableId);
                }
            }
        }
    }

    public void traverseSuccessor(MutableGraph<String> graph, String curNode, int count) {
        Set<String> successors = graph.successors(curNode);
        //代表叶子节点
        if (successors.size() == 0) {
            if ((successorNodes.containsKey(curNode) && successorNodes.get(curNode) < count) || !successorNodes.containsKey(curNode)) {
                successorNodes.put(curNode, count);
            }
            return;
        }

        Iterator successorsIter = successors.iterator();
        while (successorsIter.hasNext()) {
            curNode = (String) successorsIter.next();
            int curCount = count;

            //如果非跳过更新的节点，就count+1
            //如果结尾不是0，则代表不是跳过更新
            String last = curNode.split("_")[1];
            if (!last.equals("0")) ++count;
            traverseSuccessor(graph, curNode, count);
            count = curCount;
        }
        return;
    }

    public int longestBloodline(MutableGraph<String> graph, int count) {
        successorNodes.clear();
        int maxNodeCount = 0;
        for (String node : graph.nodes()) {

            System.out.println("node:" + node);
            if (!node.equals("") && graph.inDegree(node) == 0) {
                Set<String> successors = graph.successors(node);
                if (successors.size() == 0) {
                    if ((successorNodes.containsKey(node) && successorNodes.get(node) < count) || !successorNodes.containsKey(node)) {
                        successorNodes.put(node, count);
                    }
                    return maxNodeCount;
                }

                Iterator successorsIter = successors.iterator();
                while (successorsIter.hasNext()) {
                    node = (String) successorsIter.next();
                    int curCount = count;

                    //如果非跳过更新的节点，就count+1
                    //如果结尾不是0，则代表不是跳过更新
                    String last = node.split("_")[1];
                    if (!last.equals("0")) ++count;
                    traverseSuccessor(graph, node, count);
                    count = curCount;
                }
            }
        }

        for (Map.Entry<String, Integer> successorNode : successorNodes.entrySet()) {
            int pathContainNodes = successorNode.getValue();
            maxNodeCount = (pathContainNodes > maxNodeCount ? pathContainNodes : maxNodeCount);
        }
        return maxNodeCount;
    }

    public Set<String> getAllpredecessors(MutableGraph<String> graph, String curNode) {
        Set<String> successors = new HashSet<>();
        if(graph.nodes().contains(curNode)) {
            successors = graph.predecessors(curNode);
        }
        return successors;
    }


    public Integer getAllPredecessors(MutableGraph<String> graph, String curNode, int count) {
        Set<String> predecessors = graph.predecessors(curNode);
        if (predecessors.size() == 0) {
            return count;
        } else if (predecessors.size() == 1) {
            Iterator it = predecessors.iterator();
            if (it.next().equals("")) return count;
        }

        Iterator predecessorsIter = predecessors.iterator();
        while (predecessorsIter.hasNext()) {
            curNode = (String) predecessorsIter.next();
            if (!predecessorNodeSet.contains(curNode)) {
                predecessorNodeSet.add(curNode);
                count++;
            }

            count = getAllPredecessors(graph, curNode, count);
        }
        return count;
    }

    public PathContent getAllLayerWidth(MutableGraph<String> graph) throws IOException {
        this.graph = graph;
        PathContent path = new PathContent();
        for (String node : graph.nodes()) {
            if (!node.equals("") && graph.inDegree(node) == 0) {
                System.out.println("node:" + node);
                //用于统计当前层非跳过更新的宽度
                int nonSkipUpdatesWidth = 0;

                //创建链表，将根节点放入链表中
                LinkedList root = new LinkedList();
                root.add(node);
                RootPath rootPath = new RootPath(node);
                rootPath.updateLink.put(node, root);
                path.updateLinks.add(rootPath);
                Set<String> successors = graph.successors(node);
                LinkedList linkedList = rootPath.updateLink.remove(node);
                Iterator it = successors.iterator();
                while (it.hasNext()) {
                    LinkedList newLinkedList = (LinkedList) linkedList.clone();
                    String tableId = (String) it.next();
                    newLinkedList.add(tableId);
                    //创建相应数量的链表，并添加新后继节点
                    rootPath.updateLink.put(tableId, newLinkedList);

                    //如果结尾不是0，则代表不是跳过更新
                    String last = tableId.split("_")[1];
                    if (!last.equals("0")) {
                        nonSkipUpdatesWidth++;
                    }
                }

                rootPath.layerWidth.add(successors.size());

                //非跳过更新的宽度
                rootPath.nonSkipUpdatesLayerWidth.add(nonSkipUpdatesWidth);

                rootPath.layerWidth = getCurLayerWidth(rootPath, successors);
            }
        }
        return path;
    }

    //遍历每个graph，寻找该图中入度为零的节点，然后从根结点开始，获取当前节点的所有后继节点并记录个数
    private ArrayList getCurLayerWidth(RootPath rootPath, Set<String> successors) throws IOException {
        if (successors.size() == 0) {
            //寻找最长的链表，并打印
            */
/*for (Entry<String, LinkedList<String>> entry : rootPath.updateLink.entrySet()) {
                if (entry.getValue().size() == rootPath.layerWidth.size()) {
                    for (String tableid : entry.getValue()) {

                        System.out.print(tableid + "->");
                    }
                }
            }*//*

            return rootPath.layerWidth;
        }
        Set curLayerNodes = new HashSet();
        Iterator it = successors.iterator();
        String node = null;
        while (it.hasNext()) {
            node = (String) it.next();
            LinkedList linkedList = rootPath.updateLink.remove(node);
            if (linkedList != null) {
                Set<String> curSuccessors = graph.successors(node);
                if (curSuccessors.size() != 0) {
                    Iterator it2 = curSuccessors.iterator();
                    while (it2.hasNext()) {
                        LinkedList newLinkedList = (LinkedList) linkedList.clone();
                        String tableId = (String) it2.next();
                        newLinkedList.add(tableId);
                        */
/*for (int i = 0; i < newLinkedList.size(); i++) {
                            bufferedWriter.write(newLinkedList.get(i) + "->");
                        }
                        bufferedWriter.write("\n");*//*

                        //创建相应数量的链表，并添加新后继节点
                        rootPath.updateLink.put(tableId, newLinkedList);
                    }
                    curLayerNodes.addAll(curSuccessors);
                }
            }
        }

        //统计当前层非跳过更新的宽度
        int nonSkipUpdatesWidth = 0;
        Iterator it2 = curLayerNodes.iterator();
        while (it2.hasNext()) {
            String tableId = (String) it2.next();
            //如果结尾不是0，则代表不是跳过更新
            String last = tableId.split("_")[1];
            if (!last.equals("0")) {
                nonSkipUpdatesWidth++;
            }
        }

        rootPath.layerWidth.add(curLayerNodes.size());
        rootPath.nonSkipUpdatesLayerWidth.add(nonSkipUpdatesWidth);
        getCurLayerWidth(rootPath, curLayerNodes);
        return rootPath.layerWidth;
    }
}




















*/
