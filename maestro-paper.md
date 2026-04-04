Title: MAESTRO: Multi-Agent Evaluation Suite for

URL Source: https://arxiv.org/html/2601.00481v1

Markdown Content:
# MAESTRO: Multi-Agent Evaluation Suite for  
Testing, Reliability, and Observability

Tie Ma Beihang University , Yixi Chen KAUST , Vaastav Anand MPI-SWS , Alessandro Cornacchia KAUST , Amândio R. Faustino KAUST , Guanheng Liu Beihang University , Shan Zhang Beihang University , Hongbin Luo Beihang University , Suhaib A. Fahmy KAUST , Zafar A. Qazi LUMS & KAUST  and Marco Canini KAUST 

###### Abstract.

Large language model (LLM)-based multi-agent systems (MAS) are rapidly moving from demos to production, yet their dynamic execution makes them stochastic, failure-prone, and difficult to reproduce or debug. Existing benchmarks largely emphasize application-level outcomes (e.g., task success) and provide limited, non-standardized visibility into execution behavior, making controlled, apples-to-apples comparisons across heterogeneous MAS architectures challenging.

We present MAESTRO, an evaluation suite for the testing, reliability, and observability of LLM-based MAS. MAESTRO standardizes MAS configuration and execution through a unified interface, supports integrating both native and third-party MAS via a repository of examples and lightweight adapters, and exports framework-agnostic execution traces together with system-level signals (e.g., latency, cost, and failures). We instantiate MAESTRO with 12 representative MAS spanning popular agentic frameworks and interaction patterns, and conduct controlled experiments across repeated runs, backend models, and tool configurations. Our case studies show that MAS executions can be structurally stable yet temporally variable, leading to substantial run-to-run variance in performance and reliability. We further find that MAS architecture is the dominant driver of resource profiles, reproducibility, and cost–latency–accuracy trade-off, often outweighing changes in backend models or tool settings. Overall, MAESTRO enables systematic evaluation and provides empirical guidance for designing and optimizing agentic systems.

††conference: ; Jan 1; 2026 

## 1\. Introduction

Table 1. Summary of Systematic Findings across Case Studies (§4)

| Subject                                                                                                                                                                                                                                        | Ref.                                                                                                                                                                                                                                           | Finding                                                                                        |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Resources                                                                                                                                                                                                                                      | [§ 4.2](https://arxiv.org/html/2601.00481v1#S4.SS2 "4.2. What are the systems usage patterns and implications? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability")                         | Execution requires minimal resources: sub-GB memory, ¡20% of a CPU core, and MB-scale traffic. |
| General                                                                                                                                                                                                                                        | [§ 4.3](https://arxiv.org/html/2601.00481v1#S4.SS3 "4.3. How stable are MAS call graphs, and what factors influence their variability? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability") | Interaction structures remain stable while call sequences exhibit temporal instability.        |
| [§ 4.7](https://arxiv.org/html/2601.00481v1#S4.SS7 "4.7. How does tool usage impact cost and accuracy? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability")                                 | Tool integration mitigates speculative generation, reducing latency and cost.                                                                                                                                                                  |                                                                                                |
| Backend                                                                                                                                                                                                                                        | [§ 4.5](https://arxiv.org/html/2601.00481v1#S4.SS5 "4.5. How does model choice affect MAS behavior? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability")                                    | Model scaling yields inconsistent gains; execution dynamics dominate performance.              |
| [§ 4.6](https://arxiv.org/html/2601.00481v1#S4.SS6 "4.6. What are the dominant failure modes in LLM-based multi-agent systems? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability")         | Model-specific failures are significantly amplified by execution dynamics.                                                                                                                                                                     |                                                                                                |
| Architecture                                                                                                                                                                                                                                   | [§ 4.2](https://arxiv.org/html/2601.00481v1#S4.SS2 "4.2. What are the systems usage patterns and implications? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability")                         | MAS architecture significantly dominates resource consumption profiles.                        |
| [§ 4.3](https://arxiv.org/html/2601.00481v1#S4.SS3 "4.3. How stable are MAS call graphs, and what factors influence their variability? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability") | Architecture governs call graph similarity and determines system reproducibility.                                                                                                                                                              |                                                                                                |
| [§ 4.4](https://arxiv.org/html/2601.00481v1#S4.SS4 "4.4. How do different agent architectures affect task performance and stability? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability")   | Generalized architectures incur higher resource overhead without accuracy gains.                                                                                                                                                               |                                                                                                |
| [§ 4.7](https://arxiv.org/html/2601.00481v1#S4.SS7 "4.7. How does tool usage impact cost and accuracy? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability")                                 | Accuracy gains are architecture-dependent and contingent on low execution overhead.                                                                                                                                                            |                                                                                                |

LLM-based multi-agent systems (MAS) enable flexible task solvers that can handle diverse and multimodal workloads (ijcai2024p890) with minimal modification to the underlying system architecture. However, this flexibility also introduces substantial uncertainty in system load and execution behavior. Unlike traditional deterministic workflows, LLM-based MAS operate under a dynamic execution model in which decisions are made on the fly during runtime, driven by LLM outputs rather than by statically defined control flow.

Importantly, MAS should not be viewed merely as a collection of lightweight client-side frameworks. Instead, they constitute complex systems characterized by dynamic interactions (yan2025beyond), emergent behaviors (ijcai2024p890), and a broad spectrum of failure modes (cemri2025multi). These characteristics challenge conventional assumptions such as predictability, observability, and performance isolation, making traditional system optimization techniques less effective in this context. Therefore, a benchmark suite that systematically characterizes MAS execution behavior is essential for both system operators seeking performance optimization and researchers aiming to identify open challenges and opportunities for innovation.

Unfortunately, existing standardized benchmarks for LLM-based MAS remain limited and often lack broad coverage of MAS execution behavior. Prior work has largely focused on LLM serving and inference efficiency (wang2025burstgpt; chitty2024llm; liang2023holistic; srivastava2023beyond; hendrycks2020measuring; alpaca\_eval), evaluating server-side model performance rather than the execution behavior of agent systems. With the emergence of LLM-based MAS, recent benchmarks (liu2023agentbench; bogavelli2025agentarch; guo2024stabletoolbench; yao2024tau; geng2025realm; yan2025beyond; basu2025nestful; juneja2025magpie; sun2025collab; wang2024battleagentbench) have begun to assess individual agent capabilities (e.g., tool use and communication strategies); however, they largely remain centered on application-level performance (e.g., task success and response quality) and fall short of offering a standardized, comprehensive observability perspective on the system-level impact of MAS execution and corresponding workload management challenges. This fragmentation makes it difficult to reason about complex runtime behavior and to compare systems consistently across settings. Consistent with this gap, a recent survey (pan2025measuring) reports that nearly 75% of teams operating production MAS evaluate their systems without benchmarks, while 25% build custom benchmarks, limiting portability and reuse across scenarios.

Based on these observations, we define the following core objectives necessary for a good benchmark for LLM-based MAS:

O1: Architectural heterogeneity.The execution stack of LLM-based MAS is highly malleable. A single objective can be realized through diverse configurations, including the number of agents, role assignments, interaction topologies (e.g., centralized, hierarchical, or peer-to-peer), and communication protocols. Furthermore, the design space encompasses choices regarding orchestration frameworks, backend LLMs, budget constraints, tool availability, and memory mechanisms, as well as policies for reflection and termination.

O2: Functional representativeness.The rapid proliferation of agentic workflows and real-world deployments has led to a growing diversity of MAS architectures, many of which are optimized for specific task patterns or application domains. Recent designs explore increasingly sophisticated coordination and reasoning strategies (yao2023tree; yao2022react; shinn2023reflexion; xu2023rewoo). As a result, no single architecture can be considered representative of the broader MAS design space.

O3: Execution traceability.Current commercial agentic systems often expose high-level reasoning traces but offer limited, non-standardized visibility into execution-level details and internal system states. Furthermore, existing MAS modules lack a unified telemetry standard, often resulting in “silent” information consumption where different LLM providers and frameworks fail to expose critical operational data to the user (schoen2025stress).

To address this gap, we present MAESTRO, a comprehensive, open-source evaluation suite for LLM-based MAS. MAESTRO is designed to enable systematic characterization of execution behavior across diverse agent architectures, interaction patterns, and runtime conditions, with the goal of informing principled system optimization.

Our contributions are threefold:

Rich and extensible benchmarks.MAESTRO incorporates 12 representative MAS examples, each characterized by distinct architectural differences, to serve as a foundation for deriving systematic insights, as shown in [Table 1](https://arxiv.org/html/2601.00481v1#S1.T1 "Table 1 ‣ 1. Introduction ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability"). Moreover, MAESTRO is designed for extensibility, allowing the community to integrate and reuse existing MAS implementations within our evaluation framework with minimal effort.

Framework-agnostic system integration.MAESTRO is built upon a collection of widely used, open-source agentic frameworks and examples (langgraph; autogen; adk2025), aiming to capture common architectural patterns observed in practice rather than favoring a single workflow design.

Unified execution-level telemetry standards.MAESTRO defines and implements a unified telemetry interface designed to capture comprehensive execution data across diverse modules. This architecture establishes a common protocol that various MAS components can conform to, ensuring consistent and transparent monitoring throughout the system lifecycle.

MAESTRO is available at <https://github.com/sands-lab/maestro>.

## 2\. Background

### 2.1\. Anatomy of an LLM-based MAS

LLM-based Multi-Agent Systems (MAS) are collections of LLM agents that operate in tandem to complete large tasks that are beyond the capabilities of individual agents (guo2024large). In a typical MAS, multiple specialized agents collaborate together to plan, coordinate, and execute large tasks with each individual agent focusing on a specific sub-task.

Building blocks. An LLM agent is an entity that autonomously executes multi-step tasks by combining generative foundational models with external tools, memory, and reasoning and planning capabilities (wang2023llmagent). Agents are designed to operate autonomously in highly dynamic environments where adaptability and strategic decision making are essential. Each agent is comprised of four key parts: (i) inputs that may include user instructions, developer-specified constraints, multimodal observations, retrieved knowledge, and internal state; (ii) a generative Large Language Model (LLM) that maps the current state to decisions; (iii) an action interface that enables tool interactions such as data retrieval, API calls, code execution; (iv) outputs including user-facing responses and structured actions and artifacts along with updated state. 

Orchestration and deployment.Practitioners orchestrate MAS through workflows written in agentic programming frameworks such as LangGraph (langgraph), CrewAI (crewai), AutoGen (autogen), LlamaIndex (llamaindex), and Agno (agno). Despite the popularity of these third-party frameworks according to surveys (pan2025measuring; moshkovich2025beyond), detailed interviews with practitioners revealed that practitioners preferred to build agentic applications from scratch in 85% of the cases (pan2025measuring). These workflows may be static or dynamic depending on the degree of autonomy allowed by developers in these systems. Currently, MAS are deployed as single monolithic applications; however, they are increasingly developed and deployed as distributed applications (kagent; cornacchia2025dmas).

Workflow structure. MAS workflows often follow a hierarchical structure with task structures as a tree of sub-tasks. Individual sub-tasks follow a mix of sequential and parallel flows. Workflows may also contain recursive calls for individual agents (moshkovich2025beyond).

Failure types. MAS applications showcase three main failure types — System Design Issues, Inter-Agent Misalignment, Task Verification (cemri2025multi). System design issues include configuration issues, API and system issues, and resource mismanagement. Inter-agent misalignment issues result from a breakdown in critical information flow from inter-agent interaction and coordination during execution. This includes planning and coordination errors, incorrect output generation, individual LLM hallucinations, and incorrect information processing. Task Verification failures arise when verification strategies are inadequate at identifying issues.

Sources of non-determinism. Due to the dynamic and heterogeneous nature of MAS applications, they exhibit non-determinism due to a multitude of reasons. First, LLMs are stochastic in nature and often produce different outputs for the same input. Second, external tool executions are not pre-planned or programmed. Additionally, tools may produce non-deterministic results. Third, workflows are dynamic and change at runtime (yan2025beyond). Non-determinism in dynamic workflows may further be exacerbated due to the availability of agents. Fourth, built-in reliability mechanisms impact the performance and structure of MAS executions. For example, quality-driven retries change the execution graph.

Reliability as a first-class citizen. Typical MAS applications treat reliability as a first-class citizen as part of the design and implementation of these systems. They do so in multiple ways. First, most MAS applications rely on Human-in-the-loop evaluation, with almost half of the applications executing fewer than five steps before seeking human-in-the-loop evaluation (pan2025measuring). In addition, developers often augment applications with LLM-as-a-judge to automate quality checks. MAS applications also automate retries to improve quality if quality checks fail. Second, practitioners prioritize quality over real-time responsiveness, with 66% of respondents to a recent survey allowing response times of more than a minute (pan2025measuring). Third, practitioners prefer static workflows over dynamic workflows to constrain the autonomy of deployed agents (pan2025measuring).

### 2.2\. Limitations of existing benchmarks

Evaluating and benchmarking the performance of Large Language Models has been an important aspect in measuring the efficiency and efficacy of LLMs at executing real-world tasks (liang2023holistic; srivastava2023beyond; hendrycks2020measuring; alpaca\_eval). With the recent rise of LLM agents and MAS applications, benchmarking the performance of agentic systems has garnered a great deal of interest from the scientific community.

Agent benchmarks. Typical agent benchmarks evaluate capabilities of individual LLMs as agents (liu2023agentbench; bogavelli2025agentarch; lai2022fedscale). These benchmarks have been further extended to multi-agent settings. To do so, researchers have developed specialized benchmarks that evaluate a specific property of agentic systems such as Tool Calling (guo2024stabletoolbench; yao2024tau), Task Planning (geng2025realm), communication strategies (yan2025beyond), sequential flows (basu2025nestful), privacy preservation (juneja2025magpie), and collaboration efficacy (sun2025collab; wang2024battleagentbench). Such specialized benchmarks solely focus on one specific property or dimension of MAS applications and lack the holistic view required to effectively understand the end-to-end emergent behavior and performance of MAS applications.

Bespoke benchmarks. Due to the lack of standardization and the diversity of MAS design space, MAS application developers instead opt to create custom benchmarks specific to their application. For example, authors of Autogen (wu2024autogen) created a bespoke benchmark called Autogenbench (autogenbench) for tasks developed in the Autogen framework. According to a recent survey, 25% of teams for production MAS applications construct custom benchmarks for their applications, 75% of teams evaluate their agents without formal benchmarks and instead rely on A/B testing and direct expert/user feedback (pan2025measuring). Although these benchmarks are suitable for a given specific application, such benchmarks do not capture the diversity of the MAS design space and do not provide insight in a broad setting.

Observability tools and benchmarks. Observability tools and observability-based benchmarks such as Opik (opik2024), TRAIL (deshpande2025trail), TAMAS (moshkovich2025beyond)capture spans and traces of MAS executions which developers use to further analyze traces to triage issues and to understand MAS executions. Beyond standard metrics, such as agent call frequency, external API usage, and per-call token costs, there remains a significant gap in deep application-semantic telemetry. Addressing this requirement involves capturing granular retry logic details (e.g., attempt counts, triggers, and parent span IDs), agent-specific status conditions (e.g., failure categorization and error reasoning), and output quality assessments. Such telemetry is essential for providing the execution-level transparency needed to diagnose stochastic failures and understand complex multi-agent interactions.

## 3\. MAESTRO

We present MAESTRO, a Multi-Agent Evaluation Suite for Testing, Reliability, and Observability, as a comprehensive framework for evaluating LLM-based MAS. Building upon goals, we first outline in [§ 1](https://arxiv.org/html/2601.00481v1#S1 "1. Introduction ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability"), we detail the architecture and design of the framework ([§ 3.1](https://arxiv.org/html/2601.00481v1#S3.SS1 "3.1. Benchmark design ‣ 3. MAESTRO ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability")), illustrating how standalone MAS implementations are adapted and integrated into our suite. To demonstrate MAESTRO’s capacity for generating informative telemetry, we present a collection of representative MAS instances (i.e., the concrete evaluation units in a benchmark suite). These are categorized according to our proposed taxonomy ([§ 3.2](https://arxiv.org/html/2601.00481v1#S3.SS2 "3.2. MAS instances taxonomy ‣ 3. MAESTRO ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability")), while [§ 3.3](https://arxiv.org/html/2601.00481v1#S3.SS3 "3.3. MAS example suites studied ‣ 3. MAESTRO ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability") details the specific instances used and the formulation of evaluation suites designed to derive our experimental findings.

### 3.1\. Benchmark design

#### 3.1.1\. MAESTRO architecture

 

Figure 1. MAESTRO architecture overview.

[Figure 1](https://arxiv.org/html/2601.00481v1#S3.F1 "Figure 1 ‣ 3.1.1. MAESTRO architecture ‣ 3.1. Benchmark design ‣ 3. MAESTRO ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability") presents an overview of the MAESTRO architecture. Conceptually, MAESTRO follows a linear control flow: preparation of MAS instances, a user-defined configuration specifies how a MAS is instantiated and executed, execution traces are collected during runtime, and post-hoc processing transforms these traces into interpretable metrics and summaries. The workflow consists of five core components:

MAS instances preparation.To use MAESTRO, users first need to prepare MAS instances to be evaluated. The details of the preparation process and the supported integration modes are described in [§ 3.1.2](https://arxiv.org/html/2601.00481v1#S3.SS1.SSS2 "3.1.2. MAS instances preparation. ‣ 3.1. Benchmark design ‣ 3. MAESTRO ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability").

Configuration.Based on the prepared MAS instances, users specify the evaluation setup, including which input sources, the number and configuration of agent instances, and whether external tool access is enabled111Currently, MAESTRO only supports the adjustment of a few parameters, such as model choice and tool usage.. This configuration is passed to the _Runtime_ component for system instantiation and execution.

Runtime.Based on the provided configuration, _Runtime_ component orchestrates the execution of the MAS instances. Task inputs are continuously fed into the runtime, triggering agent interactions, tool invocations, and control-flow decisions as defined by the configuration.

Observation.During execution, the _Observation_ component monitors system behavior through function-call hooks or sampling-based instrumentation. Built on top of OpenTelemetry (opentelemetry) and psutil (psutil), it records both default execution metrics (e.g., latency, token usage; see [§ A.2.1](https://arxiv.org/html/2601.00481v1#A1.SS2.SSS1 "A.2.1. Telemetry field collection ‣ A.2. Collector implementation. ‣ Appendix A Appendix ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability")) and additional signals specified in the configuration. Collected traces are forwarded, either online or offline, to the _Post-processing_ component.

Post-processing.The _Post-processing_ component aggregates and analyzes execution traces to make MAS behavior inspectable (e.g., CPU, call graph; see [§ A.1](https://arxiv.org/html/2601.00481v1#A1.SS1 "A.1. Details of post-processing component ‣ Appendix A Appendix ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability")). These summaries enable users to explore execution trajectories, compare configurations across runs, and identify performance bottlenecks and sources of instability.

#### 3.1.2\. MAS instances preparation.

 

Figure 2. Two ways to prepare MAS instances for MAESTRO, note that MAESTRO ships with a set of built-in MAS instances that can be used and compared directly.

Before performing any evaluation, MAS instances must be integrated into MAESTRO. As illustrated in [Figure 2](https://arxiv.org/html/2601.00481v1#S3.F2 "Figure 2 ‣ 3.1.2. MAS instances preparation. ‣ 3.1. Benchmark design ‣ 3. MAESTRO ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability"), users can prepare MAS instances in two ways:222At present, MAESTRO supports only _pre-defined_ MAS instances.

* •  
MAESTRO-native. Users can implement MAS instances directly using MAESTRO’s native specification language and configuration interfaces. This mode leverages compile-based techniques (cornacchia2025dmas) to automatically generate executable instances from high-level descriptions, ensuring optimal compatibility. This mode reduces manual coding effort by generating reusable scaffolding and integration code for common components.
* •  
Third-party framework integration. Through MAESTRO’s transformation layer, users can build MAS instances in their preferred agent frameworks (e.g., ADK, LangGraph, AutoGen) or import existing open-source implementations, and connect them to MAESTRO for evaluation. The transformation layer provides a set of adapters that map framework-specific components onto MAESTRO’s standard interfaces, exposing unified entry points for configuration, execution, and telemetry collection.

MAESTRO contributors can also use these two integration modes to add new built-in MAS instances to the framework. Currently, MAESTRO has 12 built-in MAS instances (described in detail in [§ 3.3](https://arxiv.org/html/2601.00481v1#S3.SS3 "3.3. MAS example suites studied ‣ 3. MAESTRO ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability")), allowing users to perform evaluations and comparisons directly without additional integration effort.

### 3.2\. MAS instances taxonomy

A well-designed benchmark should cover a broad (O1) and representative (O2) range of system configurations and use cases; otherwise, conclusions may overfit to a narrow slice of the MAS design space and fail to generalize. To enable systematic coverage and controlled comparisons, we characterize each MAS instance using a small set of well-defined dimensions. Specifically, we describe each instance along the following axes: application field, framework, interaction pattern, and data specification. These dimensions together capture the primary sources of variation in modern MAS deployments.

Application field. The high-level domain that the MAS instance targets, which may influence task complexity, required agent capabilities, and evaluation criteria. Common fields include question answering, creative generation, finance, and others.

Framework. The underlying multi-agent framework used to implement the MAS instance, which may affect agent orchestration, communication protocols, and tool integration. General frameworks include AutoGen (wu2024autogen), ADK (adk2025), LangGraph (langgraph), and others.

Interaction pattern. The specific configuration of agents within the MAS instance, including the number of agents, the number of tools, and the cooperation type. Specifically, cooperation types include:

* •  
Planning. There is a dedicated planning agent that decomposes the task into subtasks and assigns them to other agents.
* •  
Coordination. Agents coordinate their actions through explicit communication.
* •  
Debate. Agents evaluate and compare candidate solutions to reach a consensus.
* •  
Correction. Agents collaboratively refine and improve a specific solution through iterative feedback.

These interaction patterns could affect the overall system dynamics and performance.

Data specification. The concrete input-output format and ground truth used to instantiate the MAS instance, which may influence task complexity, communication pattern, and evaluation criteria. The data specification could be divided into input and output.

* •  
Input. A task is typically instantiated via a system prompt defining its core objectives and constraints. For tasks requiring open-ended exploration, the configuration phase may also incorporate external information retrieved through auxiliary tools, such as web search engines or private databases, as supplemental inputs. Collectively, we define these structured inputs and retrieved data as _artifacts_.
* •  
Output. According to whether the output has a determined ground truth, the output could be divided into _Open-End_ and _Closed-Form_.

### 3.3\. MAS example suites studied

Table 2. Selected MAS examples overview. The “Suite” column indicates membership, F: Full Suite; A: Architecture Suite.

| Example                                  | App. Field   | Framework | Interaction | Data Spec. | Suite |           |          |     |
| ---------------------------------------- | ------------ | --------- | ----------- | ---------- | ----- | --------- | -------- | --- |
| Type                                     | #Agt         | #Tool     | In          | Out        |       |           |          |     |
| Fin. Analyzer (lastmile2024mcpfinancial) | Finance      | MCP-Agent | Correct     | 6          | 1     | Artifacts | Opn-End  | F   |
| Img. Scr. (adksamples)                   | Creativity   | ADK       | Debate      | 4          | 2     | Artifacts | Cls-Form | F   |
| Marketing (adksamples)                   | Marketing    | ADK       | Coord.      | 4          | 1     | Artifacts | Opn-End  | F   |
| Brand SEO (adksamples)                   | Marketing    | ADK       | Coord.      | 4          | 10    | Artifacts | Opn-End  | F   |
| Content Creat. (a2asamples)              | Creativity   | ADK       | Plan.       | 4          | 1     | Artifacts | Opn-End  | F   |
| Mag.-One (fourney2024magentic-one)       | Cross-domain | Autogen   | Plan        | 4          | 0     | Artifacts | Opn-End  | F   |
| Stock Res. (autogen)                     | Finance      | Autogen   | Coord.      | 4          | 2     | Artifacts | Opn-End  | F   |
| Travel Plan. (autogensamples)            | Travel       | Autogen   | Coord.      | 4          | 0     | Artifacts | Opn-End  | F   |
| ToT (yao2023tree)                        | Cross-domain | LangGraph | Debate      | 3          | 0     | Artifacts | Cls-Form | F   |
| CRAG (yan2024corrective)                 | Cross-domain | LangGraph | Coord.      | 5          | 2     | Datasets  | Opn-End  | F,A |
| Plan&Exec. (wang2023plan)                | Cross-domain | LangGraph | Plan        | 3          | 1     | Datasets  | Opn-End  | F,A |
| LATS (zhou2023language)                  | Cross-domain | LangGraph | Plan        | 3          | 1     | Datasets  | Opn-End  | F,A |

We carefully select 12 representative MAS instances to serve as the pre-defined evaluation set in MAESTRO. These instances are designed to provide sufficient coverage of common MAS configurations and use cases (O1, O2), and to act as a baseline for subsequent studies. As summarized in [Table 2](https://arxiv.org/html/2601.00481v1#S3.T2 "Table 2 ‣ 3.3. MAS example suites studied ‣ 3. MAESTRO ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability"), the selected instances are chosen according to the following criteria:

* •  
Framework diversity (O2, O3): We include examples implemented using different popular MAS frameworks, such as _MCP-Agent_, _LangGraph_, _ADK_, and _Autogen_, to capture a wide range of design patterns and interaction paradigms.
* •  
Official sources (O2): We collect examples that are provided in the official example repositories or tutorials of these frameworks, ensuring that they reflect best practices and standard usage patterns.
* •  
Domain variety (O2): We select examples that cover diverse application domains, including question answering, planning, creative writing, marketing strategy, and so on, to evaluate MAS performance across different application scenarios.
* •  
Interaction diversity (O1): We prioritize examples that exhibit varied interaction patterns among agents, such as cooperative problem solving, debate-style discussions, and role-based collaborations, to assess how different interaction styles affect MAS behavior.

As a prerequisite for meaningful analytical post-processing, MAS instances must be grouped into coherent categories that share relevant characteristics. Such grouping enables comparative analysis across multiple configurations, ensuring that observed behaviors reflect systematic trends rather than ad hoc artifacts of individual runs. To demonstrate the analytical capabilities of MAESTRO, we derive two evaluation suites, each designed to surface distinct system-level insights.

* •  
Full-suite (F): This suite includes all selected MAS examples. We treat this suite as a representative subset of real-world MAS deployments, and use it to study the overall performance and behavior of LLM-based MAS in realistic settings.
* •  
Architecture-focused suite (A): This suite includes three representative MAS examples that implement different representative multi-agent architectures but solve the same set of tasks. This suite is used to study the impact of agent architectures on MAS behavior.

 

Figure 3. Solving the same given tasks with 3 different MAS architectures.

In the architecture-focused suite, we select three representative MAS architectures: CRAG (Corrective RAG) (yan2024corrective), Plan&Execute (wang2023plan), and LATS (Language Agent Tree Search) (zhou2023language). They are designed as general-purpose agent architectures that can operate across tasks without being tightly coupled to specific applications. However, their design goals differ. As shown in [Figure 3](https://arxiv.org/html/2601.00481v1#S3.F3 "Figure 3 ‣ 3.3. MAS example suites studied ‣ 3. MAESTRO ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability"), CRAG is optimized for retrieval-centric workloads, whereas LATS and Plan-and-Execute target more general problem-solving settings, employing tree-search–based divide-and-conquer and greedy iterative refinement strategies, respectively. Such variety in the task-solver architectures enables the following comparative studies.

In the following section, we present case studies and analyses using MAESTRO, organized around these two MAS example suites.

## 4\. Case studies

To demonstrate how researchers can benefit from MAESTRO, we conduct a series of case studies that illustrate the types of insights enabled by its fine-grained telemetry. We organize our evaluation into two complementary sets of case studies:

* •  
General system-level analysis.In [§ 4.2](https://arxiv.org/html/2601.00481v1#S4.SS2 "4.2. What are the systems usage patterns and implications? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability") and [§ 4.3](https://arxiv.org/html/2601.00481v1#S4.SS3 "4.3. How stable are MAS call graphs, and what factors influence their variability? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability"), we examine system-level metrics that are not specific to MAS, but instead provide a familiar baseline for reasoning about performance, resource consumption, and reliability, analogous to evaluations in traditional systems.
* •  
Application- and semantics-aware analysis.Using Evaluation Suite 2, we investigate how different MAS solver architectures affect cost, latency, and accuracy ([§ 4.4](https://arxiv.org/html/2601.00481v1#S4.SS4 "4.4. How do different agent architectures affect task performance and stability? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability"), [§ 4.5](https://arxiv.org/html/2601.00481v1#S4.SS5 "4.5. How does model choice affect MAS behavior? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability"), [§ 4.6](https://arxiv.org/html/2601.00481v1#S4.SS6 "4.6. What are the dominant failure modes in LLM-based multi-agent systems? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability"), and [§ 4.7](https://arxiv.org/html/2601.00481v1#S4.SS7 "4.7. How does tool usage impact cost and accuracy? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability")). This analysis explores whether architectural choices and structural optimizations lead to consistent performance trade-offs, in a manner analogous to ablation studies.

### 4.1\. Methodology

Inputs.For each MAS instance, we generate evaluation inputs using one of the following three approaches:

* •  
Naive artifacts. Direct reuse of input prompts provided in the README files of official example repositories.
* •  
Public datasets. Inputs drawn from publicly available benchmark datasets aligned with the task domain of the MAS instance (e.g., question-answering datasets for QA-oriented agents (yang2018hotpotqa)).
* •  
Synthetic inputs. LLM-generated prompts that enable controlled variation and increased input diversity.

Setup. For each MAS instance, we conduct at least 20 independent runs to characterize execution behavior. Each run consists of submitting a single user-level task input to the MAS (e.g., a single “write a blog post” prompt for _Content Creation_). For MAS instances that require human-in-the-loop interaction, user responses are simulated using an LLM-as-user approach, where a designated LLM (gemini-2.5-flash in our current setup) generates replies conditioned on the MAS outputs. To prevent non-terminating execution, each run is capped at 10 minutes. For the architecture-focused suite, LLM responses are additionally limited to a maximum of 8,192 tokens. As for the external tool usage mentioned in [Table 2](https://arxiv.org/html/2601.00481v1#S3.T2 "Table 2 ‣ 3.3. MAS example suites studied ‣ 3. MAESTRO ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability"), we use Tavily or Google Search (googleSearchTool) for web search, and use Google imagen-3.0-generate-002 (googleImageGenTool) model for image generation. When correctness evaluation is required, we employ gpt-4o-mini as an LLM-as-judge. To evaluate the impact of different backbone models, we vary the underlying LLM across several configurations: Gemini-2.0-Flash-Lite (Ge20FL), Gemini-2.5-Flash-Lite (Ge25FL), Gemini-2.5-Flash (Ge25F), GPT-4o-mini (G4oM), GPT-5-mini (G5M), and GPT-5-nano (G5N).

### 4.2\. What are the systems usage patterns and implications?

Resource consumption such as CPU, memory, and network usage are important factors to consider when deploying MAS in real-world systems. Understanding the resource usage patterns of MAS can help optimize their performance and scalability. In this subsection, we analyze the resource consumption of MAS and investigate the factors that influence their usage patterns.

 

Figure 4. CPU and memory usage across different examples.

Per-task CPU and memory footprints are modest and bounded in our setup. [Figure 4](https://arxiv.org/html/2601.00481v1#S4.F4 "Figure 4 ‣ 4.2. What are the systems usage patterns and implications? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability") reports per-run CPU and memory usage across the 12 MAS examples under our runtime configuration. For CPU, the maximum observed utilization reaches 61.9%, while the boxplot distributions for most examples remain substantially below this peak, suggesting that these workloads typically do not require sustained heavy local compute. For memory, excluding the Content Creation example which peaks at 1726.8 MB, the average memory usage across examples is 200.2 MB, placing most single-task executions in a sub-GB regime in our measurements. The Content Creation example’s higher memory footprint stems from its distributed design, where each agent runs in a separate process, increasing the aggregate resident memory. We leave a broader study of distributed MAS deployments and their resource trade-offs to future work. We also observe framework-dependent memory patterns; for example, examples implemented with ADK tend to exhibit higher memory footprints in our setup.

 

Figure 5. Communication usage across different architectures.

Per-task communication volume is in the MB scale and varies by architecture and model.We further measure total communication volume across architectures with and without tools ([Figure 5](https://arxiv.org/html/2601.00481v1#S4.F5 "Figure 5 ‣ 4.2. What are the systems usage patterns and implications? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability")). Across all tested configurations, the observed communication volumes stay within the MB scale (with most cases within a few MB), indicating that, per task, network payload is typically small compared to CPU and memory footprints. It can be observed that tool usage has a minor impact on communication volume. Model choice also interacts with architecture; for example, in CRAG, Gemini-family models show larger communication volumes than GPT-family models in our measurements.

Finding 1: In our setup, most single-task executions stay within a sub-GB memory regime and bounded CPU utilization, while per-request communication remains at the MB scale. 

 

Figure 6. CPU and memory usage across different architectures.

CPU and memory usage patterns are architecture-dependent. [Figure 6](https://arxiv.org/html/2601.00481v1#S4.F6 "Figure 6 ‣ 4.2. What are the systems usage patterns and implications? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability") illustrates the CPU and memory usage grouped by architecture. Consistent with the communication patterns observed in [Figure 5](https://arxiv.org/html/2601.00481v1#S4.F5 "Figure 5 ‣ 4.2. What are the systems usage patterns and implications? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability"), resource consumption is highly architecture-dependent. CRAG exhibits the highest resource footprint, with an average CPU usage of 9.7% and memory usage of 405.3MB (averaged over all model and tool configurations). This is followed by Language Agent Tree Search (1.36% CPU) and Plan-and-Execute (0.07% CPU). We further observe that while model choice influences CPU load, it has a negligible impact on memory. Surprisingly, enabling tools reduces global average CPU usage by 3.1% and memory by 4.8MB. This phenomenon could be explained by the fact that tool usage could help reduce the number of LLM calls, which are CPU and memory-intensive.

Finding 2: Architecture dominates resource patterns, while model choice introduces smaller shifts. 

### 4.3\. How stable are MAS call graphs, and what factors influence their variability?

A distinguishing characteristic of LLM-based MAS, in contrast to traditional systems like microservices, is the inherent stochasticity of their execution behavior. In microservice architectures, call graph variability is widely used as an indicator of anomalous executions and edge cases. By extending this concept to MAS, one can leverage variability to sample a diverse and representative set of execution traces. However, a foundational stability analysis is a prerequisite for such methodologies. From a reproducibility perspective, higher call graph similarity across repeated runs implies stronger run-to-run consistency in agent interactions, and thus more reproducible MAS executions. Therefore, quantifying the stability of agent interactions across different runs and identifying the factors influencing their variability are crucial for designing robust and reproducible MAS.

We use two metrics to measure the call graph similarity: Jaccard similarity and Largest Common Sequence (LCS) similarity. These metrics capture different aspects of the call graph structure and provide insights into the agent interactions.

* •  
Jaccard similarity (edge-set overlap): For each run ii, we construct a directed call graph GiG\_{i} and denote by EiE\_{i} its (unweighted) edge set. For runs i,ji,j, we compute  
| J​(Ei,Ej)\=\|Ei∩Ej||Ei∪Ej|,J(E\_{i},E\_{j})=\\frac{|E\_{i}\\cap E\_{j}|}{|E\_{i}\\cup E\_{j}|}, |  
| ----------------------------------------------------------------------------------------------- |  
with the convention J​(Ei,Ej)\=0J(E\_{i},E\_{j})=0 when Ei∪Ej\=∅E\_{i}\\cup E\_{j}=\\emptyset. This captures whether the same interaction edges appear at least once, regardless of frequency.
* •  
LCS (order consistency): For each run ii, we linearize the calls into an ordered edge sequence SiS\_{i}. Let LCSlen​(Si,Sj)\\mathrm{LCSlen}(S\_{i},S\_{j}) denote the length of the longest common subsequence between SiS\_{i} and SjS\_{j}. We define the normalized LCS similarity as  
| LCS​(Si,Sj)\=LCSlen​(Si,Sj)max⁡(\|Si|,|Sj|),\\mathrm{LCS}(S\_{i},S\_{j})=\\frac{\\mathrm{LCSlen}(S\_{i},S\_{j})}{\\max(|S\_{i}|,|S\_{j}|)}, |  
| ------------------------------------------------------------------------------------------------------------------------------------------- |  
with the convention that two empty sequences yield 11 and one empty sequence yields 0. This measures the consistency of interaction order.

To summarize similarity at different granularities (e.g., per example, per model, or per experimental condition such as tool-on vs. tool-off), we first partition runs into groups according to the dimension of interest. For a group with nn runs, we compute similarity values for all unordered run pairs (i,j)(i,j) with 1≤i<j≤n1\\leq i<j\\leq n. For each pair, we compute J​(Ei,Ej)J(E\_{i},E\_{j}) and LCS​(Si,Sj)\\mathrm{LCS}(S\_{i},S\_{j}). We define the _pairwise average similarity_ for a group as the mean of these pairwise values over all unordered run pairs in that same group. If n<2n<2, we set the pairwise average similarity to 0 (no pairwise comparisons are available).

 

Figure 7. Cross-model call graph similarity (Jaccard Similarity: Order-agnostic overlap of agent interactions, LCS Similarity: Order-aware similarity of execution traces).

MAS execution exhibits structural stability but sequential variance.We first examine the stability of call graphs across repeated runs of the same example.[Figure 7](https://arxiv.org/html/2601.00481v1#S4.F7 "Figure 7 ‣ 4.3. How stable are MAS call graphs, and what factors influence their variability? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability") presents the intra-example average pairwise similarity for the Full Suite. We observe that across all cases there exists high Jaccard similarities (average 0.86 across all examples), indicating that the _set of agent-to-agent interactions_ remains robust against execution variance. In contrast, LCS similarity is moderate (average 0.65), suggesting that the _sequence of agent calls_ fluctuates significantly across runs. Notably, examples like CRAG and Tree-of-Thoughts demonstrate high Jaccard but low LCS scores, confirming that while the participating agents and their connections remain consistent, the temporal order of their interactions is highly dynamic. A distinct exception is the travel-planning example, which employs the RoundRobinGroupChat mechanism from _Autogen_; this enforces a deterministic execution order, resulting in perfect stability (1.0) for both metrics.

Finding 3: Across runs, MAS call graphs are largely stable in which agent-to-agent interactions occur, but often unstable in the order those interactions unfold; consequently, reproducibility is stronger at the interaction-structure level than at the execution-order level. 

 

Figure 8. Cross-model call graph LCS similarity.

Architecture determines stability, while model impact is architecture-specific.We further investigate the factors influencing call graph similarity by comparing execution patterns across different models and architectures. [Figure 8](https://arxiv.org/html/2601.00481v1#S4.F8 "Figure 8 ‣ 4.3. How stable are MAS call graphs, and what factors influence their variability? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability") presents the cross-model LCS call graph similarity heatmap, where each sub-figure corresponds to an architecture and each cell represents the median pairwise similarity between two models. We observe distinct stability profiles across architectures: CRAG exhibits extremely high consistency (average similarity 0.97 across all model pairs), whereas Language Agent Tree Search (0.54) and Plan-and-Execute (0.47) show significantly more variation. Furthermore, the impact of model choice is architecture-dependent. In CRAG, most models share identical call graphs, with gemini-2.5-flash-lite being the sole outlier. In Language Agent Tree Search, all models produce similar call graphs. Conversely, for Plan-and-Execute, gpt-4o-mini diverges significantly from other models by showing low similarity to them, yet it remains highly self-consistent across its own runs, while the remaining models tend to resemble one another.

Finding 4: MAS architecture dominates the call graph similarity, with model choice having different effects depending on the architecture. 

We then move to application-level metrics, including cost, task duration, and accuracy. Due to the inherent non-determinism of LLMs, accuracy can vary across runs; ensuring result quality therefore often correlates with increased cost and longer execution time. MAESTRO enables systematic analysis of such behavior despite the chaotic nature of LLM-driven execution. To ensure fair comparison across configurations, the following evaluation focuses exclusively on the Architecture Suite, which supports finer-grained analysis.

### 4.4\. How do different agent architectures affect task performance and stability?

 

(a) Latency versus cost per task, grouped by agent architecture. Lower values on both axes indicate better performance.

 

(b) Distribution of cost, latency, and accuracy across agent architectures; specialized designs (e.g., CRAG) achieve stable accuracy at lower cost.

Figure 9. Resource cost versus accuracy across agent architectures. Task-specific designs such as CRAG achieve comparable accuracy with lower resource cost than more general architectures like LATS.

More general-purpose solver architectures, designed to handle a wide range of complex tasks, tend to progress more cautiously. To ensure robustness, they often pause at each iteration to reflect on intermediate states. For example, Plan-and-Execute first decomposes the overall goal into a sequence of milestones and then solves each subtask incrementally. This approach helps the model maintain a comprehensive understanding of task context and often yields more reliable outcomes, but at the cost of increased execution time and resource consumption.

In contrast, when the task type is known in advance, a more specialized architecture can be employed. CRAG, for instance, is explicitly designed for retrieval-based workloads. Rather than exploring alternative reasoning paths, it prioritizes directly answering the query with minimal detours. This objective-driven design attempts to solve the task as early as possible, even with incomplete background information, trading exploration for efficiency. Such differences in design philosophy lead to substantial divergence in execution behavior across architectures.

Specialized solver minimizes resource consumption.As shown in [9(a)](https://arxiv.org/html/2601.00481v1#S4.F9.sf1 "9(a) ‣ Figure 9 ‣ 4.4. How do different agent architectures affect task performance and stability? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability"), CRAG consistently occupies the lower-cost and lower-latency region across different model choices. In particular, CRAG achieves a median cost of $0.0010 per task, which is more than an order of magnitude lower than both Plan-and-Execute (median $0.0126) and LATS (median $0.0101). CRAG also executes faster, with a median task duration of 42.8 s, compared to 101.5 s for Plan-and-Execute.

In contrast, Plan-and-Execute exhibits substantially higher variance in task duration (interquartile range 30.6–356.6 s), reflecting the overhead introduced by iterative planning and execution. LATS achieves relatively low median latency (32.3 s), but incurs higher resource cost overall.

Accuracy degrades with increasing architectural complexity.Furthermore, [9(b)](https://arxiv.org/html/2601.00481v1#S4.F9.sf2 "9(b) ‣ Figure 9 ‣ 4.4. How do different agent architectures affect task performance and stability? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability") shows that CRAG attains accuracy comparable to, and in some cases exceeding, more general architectures. CRAG achieves an average accuracy of 70.6%, compared to 48.3% for Plan-and-Execute, while also exhibiting lower variability across runs. These results indicate that task-specialized agent architectures can simultaneously reduce resource consumption and maintain strong task performance.

Notably, increased architectural complexity does not necessarily translate into higher accuracy and may even be detrimental. While it is tempting to introduce additional agents – such as fact-checkers or verification stages – to enforce desired behavior, such designs inevitably increase execution cost and prolong interaction histories. In our evaluation, Plan-and-Execute spends substantially more time reasoning over tasks yet achieves lower accuracy (average 48.3% vs. 70.6% for CRAG), despite incurring significantly higher execution cost. This behavior aligns with prior findings that model performance degrades as interaction histories grow longer, due to diminishing attention to earlier context and error accumulation in extended reasoning chains (liu2024lost).

Finding 5: More general agent architectures consume more resources and do not consistently improve accuracy. 

### 4.5\. How does model choice affect MAS behavior?

A natural assumption in LLM-based MAS design is that upgrading the underlying model should improve system performance. Intuitively, scaling to more capable models is expected to increase cost while yielding higher accuracy. However, our experimental results challenge this assumption. We find that stronger models do not necessarily incur substantially higher costs in practice, nor do they consistently lead to improved correctness. Instead, model choice affects MAS behavior in more nuanced and sometimes counterintuitive ways.

Stronger models reduce iteration overhead rather than total cost.More capable models often complete subtasks with fewer iterations, reducing pathological behaviors such as repeated retries or prolonged refinement loops. However, these efficiency gains primarily offset higher per-token pricing rather than translating into lower overall cost. For example, gpt-5-mini and gpt-5-nano exhibit comparable mean cost per task (0.033 vs. 0.043), despite differences in model size, while gpt-4o-mini achieves substantially lower median cost (0.0034) than both. Similarly, execution latency is non-monotonic: gpt-4o-mini completes tasks faster (median 45.3 s) than the larger 5-series models, whereas gpt-5-nano is slower than gpt-5-mini despite being nominally smaller. These results indicate that model choice influences iteration efficiency and tail behavior, but does not induce a clear cost hierarchy.

Accuracy exhibits non-monotonic and unstable trends across models.We further observe no consistent relationship between model strength and task accuracy. While gpt-5-mini achieves the highest accuracy (median 81%), weaker or similarly priced models do not follow a predictable trend: gpt-5-nano trails at 65%, and gpt-4o-mini exhibits high median accuracy (71%) but a substantially lower mean (48%), indicating unstable behavior with heavy failure cases. Gemini models cluster around similar accuracy levels (approximately 66%), with the 2.0-lite variant performing worse overall. These results suggest that MAS accuracy is highly sensitive to execution dynamics and variance amplification, rather than model capacity alone, and that upgrading the base model is insufficient to guarantee improved correctness.

Finding 6: Upgrading the base LLM does not reliably reduce cost or improve accuracy in MAS, as execution dynamics dominate model-level gains. 

 

Figure 10. Cost–duration–accuracy trade-offs across LLMs; efficiency improves for Gemini-family models, while accuracy shows no clear scaling trend.

### 4.6\. What are the dominant failure modes in LLM-based multi-agent systems?

We find that most failures manifest as silent gray errors (75.17% in [Table 3](https://arxiv.org/html/2601.00481v1#S4.T3 "Table 3 ‣ 4.6. What are the dominant failure modes in LLM-based multi-agent systems? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability")), which do not trigger explicit system failures and are therefore not immediately visible to users. These errors only become apparent upon manual inspection of the output. Importantly, such failures are not system-level exceptions, but rather plausible-looking yet unusable responses. As a result, failure attribution in LLM-based MAS is particularly challenging, since erroneous executions often complete without emitting any hard error signals.

Table 3. Global failure composition across all experiments.

| Failure category                | Percentage (%) |
| ------------------------------- | -------------- |
| Missing / underspecified output | 47.61          |
| Wrong fact / entity             | 27.66          |
| Empty prediction                | 15.96          |
| Exception                       | 6.38           |
| Timeout                         | 1.86           |
| Other                           | 0.54           |
| Silent semantic failures        | 75.17          |
| Explicit failures               | 24.84          |

We further break down failure causes by model in [11(a)](https://arxiv.org/html/2601.00481v1#S4.F11.sf1 "11(a) ‣ Figure 11 ‣ 4.6. What are the dominant failure modes in LLM-based multi-agent systems? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability"), which reveals distinct, model-specific failure signatures. Rather than failing uniformly, different LLM backends exhibit characteristic behaviors when errors occur.

Model-specific failure patterns.

* •  
Gemini-2.0-flash-lite predominantly fails by producing underspecified or incomplete outputs, where a response is returned but lacks sufficient detail to satisfy task requirements.
* •  
Gemini-2.5-flash-lite exhibits a more conservative failure mode, frequently abstaining and returning empty or null outputs when uncertain.
* •  
GPT-4o-mini tends to produce fully formed but factually incorrect responses, committing confidently to wrong entities or facts rather than omitting answers.

These distinct failure signatures indicate that MAS failures are not only model-dependent, but also shaped by how agent architectures interpret and propagate partial outputs. Consequently, failures emerge as execution-path–dependent phenomena rather than isolated faults attributable to a single component.

Finding 7: MAS failures predominantly manifest as silent semantic errors, with distinct, model-specific failure signatures that are amplified by execution dynamics. 

Divergent failure attribution across LLM-as-judges.To assess the reliability of LLM-as-judge–based failure attribution, we perform offline analysis using three additional judge models, each provided with the final MAS response and the corresponding gold answer. As shown in [11(b)](https://arxiv.org/html/2601.00481v1#S4.F11.sf2 "11(b) ‣ Figure 11 ‣ 4.6. What are the dominant failure modes in LLM-based multi-agent systems? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability"), offline attribution struggles to correctly identify system-level failures, such as exceptions or timeouts, due to the absence of runtime execution signals.

For example, a MAS execution may enter a non-terminating review loop that repeatedly generates responses containing the correct answer but never produces a valid final output. During online execution, such behavior is correctly identified as a failure, since the task does not terminate successfully. In contrast, an offline judge, which only observes the final response and history, may incorrectly classify the execution as successful because the correct answer appears in the trace.

Even for semantic-based gray failures, where judges often agree on whether an execution is broadly correct or incorrect (e.g., all judges consistently identify CRAG executions as successful), substantial divergence arises in the attribution of failure _types_. For instance, when a MAS responds with:_“I am sorry, I cannot answer this question. The available tools do not have the functionality to determine the country of a member of the Gujarat Legislative Assembly and parliament.”_the gpt-oss-120b judge classifies this outcome as an _empty prediction_, whereas gemini-2.5-flash attributes it to a _wrong fact/entity_.

These discrepancies highlight that, even under identical inputs and failure definitions, LLM-based judges may disagree on fine-grained failure attribution, underscoring the inherent subjectivity and instability of offline, semantics-only failure analysis.

 

(a) Online failure attribution via LLM-as-judge (GPT-4o-mini).

 

(b) Offline failure attribution via LLM-as-judge (Gemini-2.5-Flash, GPT-4o, GPT-OSS-120B).

Figure 11. Failure attribution using different LLM judges. We prioritize online attribution when possible, as it incorporates runtime signals unavailable offline, such as execution stalls and incomplete system outputs. For offline attribution, judges are provided with the final MAS response, the corresponding gold answer, and an identical failure taxonomy. Despite controlling inputs, attribution results exhibit substantial variance across judge models, highlighting the inherent subjectivity and instability of LLM-based failure attribution.

### 4.7\. How does tool usage impact cost and accuracy?

A common assumption in LLM-based MAS design is that enabling external tools should improve task performance. By equipping agents with additional information sources or capabilities, one would expect higher-quality outputs and, consequently, improved accuracy. However, our results indicate that the impact of tool usage is highly dependent on the underlying agent architecture.

Enabling web search commonly increases resource consumption.Overall, enabling external tools tends to increase resource consumption, but accuracy gains are not uniform across architectures. As shown in [12(a)](https://arxiv.org/html/2601.00481v1#S4.F12.sf1 "12(a) ‣ Figure 12 ‣ 4.7. How does tool usage impact cost and accuracy? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability"), tool usage introduces different overheads depending on how tools are integrated into the execution workflow. For CRAG, external tools primarily increase monetary cost, with a median cost increase of $0.0010 per task and a modest median latency increase of 8.1 s, reflecting additional retrieval and processing steps. In contrast, Plan-and-Execute experiences a substantial increase in task duration, with a median latency increase of 34.1 s, while its monetary cost slightly decreases, indicating that overhead is shifted toward longer execution rather than additional token usage. LATS exhibits the highest overall overhead, with tool usage increasing both execution time and cost, suggesting compounded interaction and coordination overheads.

When web search reduces task duration.While external tools typically introduce additional overhead, we observe notable outliers where web search reduces overall execution cost and latency. In particular, for CRAG with gpt-5-nano, enabling web search results in faster task completion (by approximately 2 s on average). This effect arises because, in the absence of external evidence, the model tends to generate longer, more speculative responses, increasing both token usage and per-round LLM latency. Trace-level analysis confirms this behavior: in no-search executions, the generator and grader produce longer outputs, substantially increasing per-call latency, whereas providing web evidence shortens responses and reduces LLM latency (median generator time 11.2 s to 6.1 s). As a result, CRAG with web search achieves 13.9% lower mean task duration despite the additional retrieval step, indicating that external context can reduce speculative reasoning and offset tool overhead.

When web search reduces planning cost.For Plan-and-Execute, enabling web search often leads to a net reduction in cost, as external evidence allows the planner to generate more concrete and concise plans. Without web search, the planner tends to produce longer, speculative plans, and the replanner emits more verbose messages to justify or revise these plans, inflating token usage.

Trace-level evidence supports this observation: across models, planner messages are substantially shorter when web search is enabled (e.g., average planner tokens drop from over 1,500 to a few hundred per call), and replanner turns are also more concise. Although the number of planning or replanning iterations may remain similar – or even increase slightly – the reduction in per-turn token usage outweighs the cost of the additional web retrieval step, resulting in lower overall execution cost.

Finding 8: By providing external context, tools can reduce speculative generation, lowering inference time and cost. 

Web search boosts accuracy, but non-uniformly across architectures.Tool usage yields markedly different outcomes across agent architectures. As shown in [12(b)](https://arxiv.org/html/2601.00481v1#S4.F12.sf2 "12(b) ‣ Figure 12 ‣ 4.7. How does tool usage impact cost and accuracy? ‣ 4. Case studies ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability"), CRAG consistently benefits from external tools, achieving a median accuracy improvement of 35.7% and improving accuracy in 83.3% of evaluated runs. In contrast, Plan-and-Execute loss minor median accuracy, with improvements observed in only one third of runs. LATS shows marginal and unstable gains, with a median accuracy improvement of 4.2% and positive effects in only half of the cases.

In conclusion, these accuracy trends align with the associated cost and latency overheads. CRAG incurs only modest increases in cost and execution time, whereas Plan-and-Execute primarily shifts overhead to longer execution latency, and LATS experiences increases in both cost and latency. Together, these results indicate that external tools improve MAS performance only when the underlying architecture can incorporate them without amplifying execution complexity or instability.

Finding 9: External tools improve accuracy only when the agent architecture can integrate them without amplifying execution overhead or variance. 

 

(a) Impact of enabling the Web Search tool. We measure the deltas in execution latency and monetary costs, after enabling the web search tool.

 

(b) Accuracy deltas after enabling web search.

Figure 12. Resource cost versus accuracy across agent architectures. Task-specific designs such as CRAG achieve comparable accuracy with lower resource cost than more general architectures like LATS.

## 5\. Discussion

While MAESTRO already provides valuable insights into the behavior of LLM-based MAS, significant opportunities for extension remain.

### 5.1\. Limitation

Generalizability.Given the inherent heterogeneity (D1) of LLM-based MAS, it is difficult to identify a single canonical architecture or execution pattern that generalizes across all agentic systems. The design space of MAS continues to evolve rapidly, with new coordination strategies, tooling abstractions, and execution models emerging at a fast pace.

While MAESTRO is designed to cover a diverse set of widely used MAS architectures and workflows, the insights derived from our evaluation are necessarily grounded in the specific instances and configurations studied. As a result, some findings may not directly transfer to future MAS designs or to application domains not represented in our benchmark. In particular, advances in agent orchestration or model capabilities may invalidate certain observations over time, highlighting the need for continuously evolving benchmarks alongside the MAS ecosystem.

Overhead of telemetry.MAESTRO incorporates fine-grained telemetry to examine per-step behavior in LLM-based MAS and derive detailed insights into execution dynamics. However, such instrumentation introduces profiling overhead that may degrade system performance. Before real-world deployment, MAESTRO must therefore optimize telemetry collection to minimize overhead, for example, through sampling strategies, adaptive logging, or lightweight monitoring mechanisms.

### 5.2\. Future works

Automated integration for MAS instances.Currently, MAESTRO includes a limited representative set of MAS examples, which may not fully capture the diversity and complexity of real-world deployments. To improve representativeness, the benchmark must incorporate a broader range of MAS examples that reflect the diversity of real-world deployments and use cases. At present, fine-grained telemetry is enabled through ad-hoc instrumentation tailored to individual MAS frameworks. As future work, we plan to develop an automated translation layer that maps heterogeneous agent implementations into a uniform execution representation, enabling systematic behavior capture with minimal manual intervention. Such automated integration would also lower the barrier for external contributions, allowing developers to more easily evaluate their own MAS implementations using our test suite.

Monolith vs. distributed. Similar to the relationship between monolithic applications and microservices in traditional software architectures, LLM-based MAS can be deployed either as a single, unified system or as a collection of distributed agents communicating over a network. Distributed deployments could bring benefits such as improved fault tolerance, scalability, and modularity. However, they also introduce challenges related to network latency, synchronization, and consistency. Future work could explore the trade-offs between monolithic and distributed MAS architectures, evaluating their performance, reliability, and resource utilization under various workloads and deployment scenarios. Also, it would be interesting to investigate the impact of the underlying network infrastructure on the behavior and performance of distributed LLM-based MAS.

MAS-specific failure attribution.The inherent non-determinism of LLMs introduces failure modes that are rarely encountered in traditional deterministic systems. When multiple agents are composed into a pipeline, these effects are further amplified, increasing the likelihood of inconsistent or emergent failure behaviors. Such phenomena are already observed in our evaluation. For instance, in the Plan-and-Execute architecture, we identify recurring execution patterns in which the executor successfully retrieves and returns the gold answer, yet the replanner repeatedly rejects the intermediate result. This mismatch prevents the system from reaching a terminal state, ultimately leading to timeouts despite the presence of a correct solution in the execution trace. These observations highlight the difficulty of failure attribution in LLM-based MAS. Due to the extensive fault space induced by LLM heterogeneity (D1), which grows combinatorially as multiple agents and models interact, failures often cannot be localized to a single component or decision point. Developing principled failure taxonomies and robust attribution mechanisms for such systems therefore remains an important direction for future work.

Communication mechanisms.Our experiments reveal substantial variation in how different MAS frameworks implement inter-agent communication. In many of the frameworks we evaluate, agents primarily interact through structured function calls. Others rely on a shared global scratchpad that allows agents to read from and write to a common intermediate state.

For interactions beyond a single host or for accessing external data sources, some frameworks additionally support standardized communication protocols, such as agent-to-agent (A2A) (a2aProtocol) messaging or the Model Context Protocol (MCP) (mcp). These differences in communication mechanisms introduce distinct execution semantics and coordination patterns, yet their impact on system performance, robustness, and failure behavior remains largely unexplored. This observation highlights an open research area in understanding how communication design choices influence the behavior of LLM-based MAS.

Parallelism and coordination effects.Parallelism fundamentally alters the execution dynamics of LLM-based MAS, affecting not only throughput and resource utilization but also coordination behavior and failure modes. While parallel execution and load balancing are well-established techniques in traditional systems, their impact in asynchronous MAS remains poorly understood.

Existing work has extensively studied single-LLM optimizations, such as speculative inference and parallel decoding (leviathan2023fast; chen2023accelerating), to improve accuracy or cost–performance trade-offs. However, it is unclear how these techniques translate to multi-agent settings, where multiple agents may operate concurrently and interact through shared state or tools.

In particular, the effects of parallel agents with overlapping or partially redundant roles are not yet well characterized. Such configurations may introduce new coordination overheads, contention, or emergent behaviors that differ fundamentally from single-model parallelism, highlighting an important direction for future investigation.

Framework overhead investigation. In our evaluation, we observe that kagent (kagent), a framework designed to facilitate building distributed LLM-based multi-agent systems, can incur non-trivial communication overhead and may also trigger operational failures (e.g., a disk-full error on the kagent controller node). Future work should systematically characterize the overheads introduced by MAS frameworks and quantify their impact on end-to-end performance and reliability.

## 6\. Conclusion

We argue that LLM-based multi-agent systems (MAS) must be evaluated not merely by task completion, but as complex systems characterized by dynamic, stochastic execution. To this end, we introduce MAESTRO, an open-source evaluation suite that standardizes the configuration and execution of heterogeneous MAS while exporting fine-grained, system-level telemetry to enable cross-stack comparison.

Our evaluation of 12 representative MAS instances reveals that while agentic workflows are often _structurally_ stable, they exhibit significant _temporal_ instability, driving high run-to-run variance in latency, cost, and failure modes. Crucially, we find that MAS architecture dominates backend model and toolset choices in determining resource profiles, reproducibility, and the cost–latency–accuracy trade-off. These findings indicate that optimizing reliability and efficiency in agentic systems is fundamentally an architectural challenge, necessitating benchmarks that prioritize deep execution visibility over simple application-level scores.

Looking ahead, we plan to extend MAESTRO to support distributed architectures and automated agent integration, while refining failure attribution to better diagnose stochastic errors. Our ultimate goal is to establish standardized observability contracts, ensuring that benchmarking keeps pace with the evolving complexity of agentic systems.

## Appendix A Appendix

### A.1\. Details of post-processing component

We build an observation component that characterizes MAS behavior across benchmark tasks and configurations. By default, we generate a common set of plots for each workload. We report results both for individual executions and aggregated across multiple runs. Because the full set of figures is large, we plan to release them as a dataset and provide only a brief summary here.

* •  
Token consumption. For the single run, we plot the token consumption of each agent over time, including prompt tokens and completion tokens; we also plot the total token consumption of all agents over time. For multiple runs, we plot the average total token consumption of all agents over time.
* •  
Delay. For the single run, we plot the end-to-end delay of the whole system, and decompose it into agent processing delay, agent-to-LLM communication delay, and agent-to-agent communication delay. For multiple runs, we plot the average end-to-end delay of the whole system. We plot the breakdown of the average delay into different components. We also plot a flame graph for delay.
* •  
CPU and memory usage. For the single run, we plot the time series of CPU and memory usage of the whole system. We also give a correlation analysis between CPU/memory usage and system events (e.g., agent invocations, LLM calls, etc.). For multiple runs, we plot the mean, peak, and minimum CPU and memory usage of the whole system.
* •  
Message size. For the single run, we plot the average input and output message size of each agent for both agent-to-agent messages and agent-to-LLM messages. For multiple runs, we plot the total input and output message size of agent-to-agent messages and agent-to-LLM messages. We also plot per-agent, per-agent-pair, and per-agent-to-LLM message sizes.
* •  
Call graph. We visualize the call graph of the agents in the system. We also show the similarity between the call graphs of different runs using graph similarity metrics. We use two similarity metrics: Jaccard similarity and Largest Common Subgraph (LCS) similarity. Jaccard similarity measures the similarity between two sets of edges in the call graphs, while LCS similarity measures the sequence similarity of the edges in the call graphs.

### A.2\. Collector implementation.

#### A.2.1\. Telemetry field collection

The following listing (Listing [1](https://arxiv.org/html/2601.00481v1#LST1 "Listing 1 ‣ A.2.1. Telemetry field collection ‣ A.2. Collector implementation. ‣ Appendix A Appendix ‣ MAESTRO: Multi-Agent Evaluation Suite for Testing, Reliability, and Observability")) shows a collection of telemetry fields in MAESTRO.

Listing 1: Telemetry field collection

[⬇](data:text/plain;base64,WwogIHsKICAgICJ0cmFjZV9pZCI6ICI8MzItaGV4LXRyYWNlLWlkPiIsCiAgICAic3Bhbl9pZCI6ICI8MTYtaGV4LXNwYW4taWQ+IiwKICAgICJwYXJlbnRfc3Bhbl9pZCI6ICI8MTYtaGV4LXBhcmVudC1zcGFuLWlkLW9yLW51bGw+IiwKICAgICJuYW1lIjogIjxvcGVyYXRpb24tbmFtZT4iLAogICAgImFnZW50X25hbWUiOiAiPGFnZW50LW5hbWU+IiwKICAgICJzdGFydF90aW1lIjogMCwKICAgICJlbmRfdGltZSI6IDAsCiAgICAiZHVyYXRpb25fbnMiOiAwLAogICAgImtpbmQiOiAiPElOVEVSTkFMfFNFUlZFUnxDTElFTlR8UFJPRFVDRVJ8Q09OU1VNRVI+IiwKICAgICJzdGF0dXMiOiB7CiAgICAgICJzdGF0dXNfY29kZSI6ICI8VU5TRVR8T0t8RVJST1I+IiwKICAgICAgImRlc2NyaXB0aW9uIjogIjxvcHRpb25hbC1kZXNjcmlwdGlvbj4iCiAgICB9LAogICAgImF0dHJpYnV0ZXMiOiB7CiAgICAgICJnZW5fYWkub3BlcmF0aW9uLm5hbWUiOiAiPGNhbGxfbGxtfGV4ZWN1dGVfdG9vbHxpbnZva2VfYWdlbnQ+IiwKICAgICAgImdlbl9haS5zeXN0ZW0iOiAiPHByb3ZpZGVyPiIsCiAgICAgICJnZW5fYWkuYWdlbnQubmFtZSI6ICI8YWdlbnQtbmFtZT4iLAogICAgICAiZ2VuX2FpLmFnZW50LmRlc2NyaXB0aW9uIjogIjxvcHRpb25hbC1kZXNjcmlwdGlvbj4iLAogICAgICAiZ2VuX2FpLnJlcXVlc3QubW9kZWwiOiAiPG1vZGVsPiIsCiAgICAgICJnZW5fYWkuY29udmVyc2F0aW9uLmlkIjogIjxjb252ZXJzYXRpb24taWQ+IiwKICAgICAgImdlbl9haS50b29sLm5hbWUiOiAiPHRvb2wtbmFtZT4iLAogICAgICAiZ2VuX2FpLnRvb2wudHlwZSI6ICI8RnVuY3Rpb25Ub29sfEJ1aWx0aW4+IiwKICAgICAgImdlbl9haS50b29sLmNhbGwuaWQiOiAiPHRvb2wtY2FsbC1pZD4iLAogICAgICAiZ2VuX2FpLnRvb2wuZGVzY3JpcHRpb24iOiAiPHRvb2wtZGVzY3JpcHRpb24+IiwKICAgICAgImdlbl9haS51c2FnZS5pbnB1dF90b2tlbnMiOiAwLAogICAgICAiZ2VuX2FpLnVzYWdlLm91dHB1dF90b2tlbnMiOiAwLAogICAgICAiZ2VuX2FpLnVzYWdlLnRvdGFsX3Rva2VucyI6IDAsCiAgICAgICJnZW5fYWkubGxtLmNhbGwuY291bnQiOiAwLAogICAgICAiZ2VuX2FpLm1jcC5jYWxsLmNvdW50IjogMCwKICAgICAgImdlbl9haS5yZXNwb25zZS5maW5pc2hfcmVhc29ucyI6IFtdLAogICAgICAibWNwLnNlcnZlciI6ICI8c2VydmVyLW5hbWU+IiwKICAgICAgIm1jcC50b29sIjogIjx0b29sLW5hbWU+IiwKICAgICAgImdjcC52ZXJ0ZXguYWdlbnQubGxtX3JlcXVlc3QiOiAiPHJhdy1yZXF1ZXN0LWpzb24+IiwKICAgICAgImdjcC52ZXJ0ZXguYWdlbnQubGxtX3Jlc3BvbnNlIjogIjxyYXctcmVzcG9uc2UtanNvbj4iLAogICAgICAiZ2NwLnZlcnRleC5hZ2VudC50b29sX2NhbGxfYXJncyI6ICI8dG9vbC1jYWxsLWFyZ3M+IiwKICAgICAgImdjcC52ZXJ0ZXguYWdlbnQudG9vbF9yZXNwb25zZSI6ICI8dG9vbC1yZXNwb25zZT4iLAogICAgICAiZ2NwLnZlcnRleC5hZ2VudC5pbnZvY2F0aW9uX2lkIjogIjxpbnZvY2F0aW9uLWlkPiIsCiAgICAgICJnY3AudmVydGV4LmFnZW50LnNlc3Npb25faWQiOiAiPHNlc3Npb24taWQ+IiwKICAgICAgImdjcC52ZXJ0ZXguYWdlbnQuZXZlbnRfaWQiOiAiPGV2ZW50LWlkPiIsCiAgICAgICJhZ2VudC5sb2ciOiAiPG9wdGlvbmFsLWxvZy1saW5lPiIsCiAgICAgICJhZ2VudC5yZXRyeS5hdHRlbXB0X251bWJlciI6IDAsCiAgICAgICJhZ2VudC5yZXRyeS50cmlnZ2VyIjogIjxxdWFsaXR5fHJlbGV2YW5jZV9ndWFyZHxndWFyZF9mYWlsfHRpbWVvdXR8c3lzdGVtfHVwc3RyZWFtPiIsCiAgICAgICJhZ2VudC5yZXRyeS5wcmV2aW91c19zcGFuX2lkIjogIjwxNi1oZXgtc3Bhbi1pZC1vci1udWxsPiIsCiAgICAgICJhZ2VudC5yZXRyeS5yZWFzb24iOiAiPG9wdGlvbmFsLXJldHJ5LXRyaWdnZXI+IiwKICAgICAgInJ1bi5vdXRjb21lIjogIjxzdWNjZXNzfGZhaWx1cmU+IiwKICAgICAgInJ1bi5vdXRjb21lX3JlYXNvbiI6ICI8b3B0aW9uYWwtcmVhc29uPiIsCiAgICAgICJydW4uanVkZ2VtZW50IjogIjxjb3JyZWN0fHdyb25nfHVua25vd24+IiwKICAgICAgInJ1bi5qdWRnZW1lbnRfcmVhc29uIjogIjxvcHRpb25hbC1yZWFzb24+IiwKICAgICAgImFnZW50LmZhaWx1cmUuY2F0ZWdvcnkiOiAiPGd1YXJkfHF1YWxpdHl8c3lzdGVtfHRpbWVvdXR8dXBzdHJlYW0+IiwKICAgICAgImFnZW50LmZhaWx1cmUucmVhc29uIjogIjxmcmVlLXRleHQ+IiwKICAgICAgImFnZW50Lm91dHB1dC51c2VsZXNzIjogZmFsc2UsCiAgICAgICJhZ2VudC5vdXRwdXQudXNlbGVzc19yZWFzb24iOiAiPGZyZWUtdGV4dD4iLAogICAgICAiY29tbXVuaWNhdGlvbi5pbnB1dF9tZXNzYWdlX3NpemVfYnl0ZXMiOiAwLAogICAgICAiY29tbXVuaWNhdGlvbi5vdXRwdXRfbWVzc2FnZV9zaXplX2J5dGVzIjogMCwKICAgICAgImNvbW11bmljYXRpb24udG90YWxfbWVzc2FnZV9zaXplX2J5dGVzIjogMAogICAgfSwKICAgICJjb21tdW5pY2F0aW9uIjogewogICAgICAiaXNfaW5fcHJvY2Vzc19jYWxsIjogZmFsc2UsCiAgICAgICJpbnB1dF9tZXNzYWdlX3NpemVfYnl0ZXMiOiAwLAogICAgICAib3V0cHV0X21lc3NhZ2Vfc2l6ZV9ieXRlcyI6IDAsCiAgICAgICJ0b3RhbF9tZXNzYWdlX3NpemVfYnl0ZXMiOiAwCiAgICB9LAogICAgInJlc291cmNlIjogewogICAgICAiYXR0cmlidXRlcyI6IHsKICAgICAgICAic2VydmljZS5uYW1lIjogIjxzZXJ2aWNlLW5hbWU+IiwKICAgICAgICAic2VydmljZS52ZXJzaW9uIjogIjxzZW12ZXI+IiwKICAgICAgICAiZGVwbG95bWVudC5lbnZpcm9ubWVudCI6ICI8bG9jYWx8ZGV2fHN0YWdpbmd8cHJvZD4iLAogICAgICAgICJ0ZWxlbWV0cnkuc2RrLm5hbWUiOiAiPHNkay1uYW1lPiIsCiAgICAgICAgInRlbGVtZXRyeS5zZGsubGFuZ3VhZ2UiOiAiPGxhbmd1YWdlPiIsCiAgICAgICAgInRlbGVtZXRyeS5zZGsudmVyc2lvbiI6ICI8dmVyc2lvbj4iLAogICAgICAgICJob3N0Lm5hbWUiOiAiPG9wdGlvbmFsLWhvc3Q+IgogICAgICB9CiAgICB9CiAgfQpd)

1\[ 

2 { 

3 "trace\_id": "<32-hex\-trace\-id\>", 

4 "span\_id": "<16-hex\-span\-id\>", 

5 "parent\_span\_id": "<16-hex\-parent\-span\-id\-or\-null\>", 

6 "name": "<operation\-name\>", 

7 "agent\_name": "<agent\-name\>", 

8 "start\_time": 0, 

9 "end\_time": 0, 

10 "duration\_ns": 0, 

11 "kind": "<INTERNAL|SERVER|CLIENT|PRODUCER|CONSUMER\>", 

12 "status": { 

13 "status\_code": "<UNSET|OK|ERROR\>", 

14 "description": "<optional\-description\>" 

15 }, 

16 "attributes": { 

17 "gen\_ai.operation.name": "<call\_llm|execute\_tool|invoke\_agent\>", 

18 "gen\_ai.system": "<provider\>", 

19 "gen\_ai.agent.name": "<agent\-name\>", 

20 "gen\_ai.agent.description": "<optional\-description\>", 

21 "gen\_ai.request.model": "<model\>", 

22 "gen\_ai.conversation.id": "<conversation\-id\>", 

23 "gen\_ai.tool.name": "<tool\-name\>", 

24 "gen\_ai.tool.type": "<FunctionTool|Builtin\>", 

25 "gen\_ai.tool.call.id": "<tool\-call\-id\>", 

26 "gen\_ai.tool.description": "<tool\-description\>", 

27 "gen\_ai.usage.input\_tokens": 0, 

28 "gen\_ai.usage.output\_tokens": 0, 

29 "gen\_ai.usage.total\_tokens": 0, 

30 "gen\_ai.llm.call.count": 0, 

31 "gen\_ai.mcp.call.count": 0, 

32 "gen\_ai.response.finish\_reasons": \[\], 

33 "mcp.server": "<server\-name\>", 

34 "mcp.tool": "<tool\-name\>", 

35 "gcp.vertex.agent.llm\_request": "<raw\-request\-json\>", 

36 "gcp.vertex.agent.llm\_response": "<raw\-response\-json\>", 

37 "gcp.vertex.agent.tool\_call\_args": "<tool\-call\-args\>", 

38 "gcp.vertex.agent.tool\_response": "<tool\-response\>", 

39 "gcp.vertex.agent.invocation\_id": "<invocation\-id\>", 

40 "gcp.vertex.agent.session\_id": "<session\-id\>", 

41 "gcp.vertex.agent.event\_id": "<event\-id\>", 

42 "agent.log": "<optional\-log\-line\>", 

43 "agent.retry.attempt\_number": 0, 

44 "agent.retry.trigger": "<quality|relevance\_guard|guard\_fail|timeout|system|upstream\>", 

45 "agent.retry.previous\_span\_id": "<16-hex\-span\-id\-or\-null\>", 

46 "agent.retry.reason": "<optional\-retry\-trigger\>", 

47 "run.outcome": "<success|failure\>", 

48 "run.outcome\_reason": "<optional\-reason\>", 

49 "run.judgement": "<correct|wrong|unknown\>", 

50 "run.judgement\_reason": "<optional\-reason\>", 

51 "agent.failure.category": "<guard|quality|system|timeout|upstream\>", 

52 "agent.failure.reason": "<free\-text\>", 

53 "agent.output.useless": false, 

54 "agent.output.useless\_reason": "<free\-text\>", 

55 "communication.input\_message\_size\_bytes": 0, 

56 "communication.output\_message\_size\_bytes": 0, 

57 "communication.total\_message\_size\_bytes": 0 

58 }, 

59 "communication": { 

60 "is\_in\_process\_call": false, 

61 "input\_message\_size\_bytes": 0, 

62 "output\_message\_size\_bytes": 0, 

63 "total\_message\_size\_bytes": 0 

64 }, 

65 "resource": { 

66 "attributes": { 

67 "service.name": "<service\-name\>", 

68 "service.version": "<semver\>", 

69 "deployment.environment": "<local|dev|staging|prod\>", 

70 "telemetry.sdk.name": "<sdk\-name\>", 

71 "telemetry.sdk.language": "<language\>", 

72 "telemetry.sdk.version": "<version\>", 

73 "host.name": "<optional\-host\>" 

74 } 

75 } 

76 } 

77\] 

#### A.2.2\. Lacking of standardized observability contracts.

Even when a common observability schema (e.g., OTEL) is imposed, orchestration stacks differ substantially in which telemetry signals are surfaced, transformed, or suppressed. While some frameworks propagate execution metadata such as token usage, termination reasons, or payload sizes to application-level hooks, others consume these signals within internal execution layers without exposing them externally. As a result, identical agent workflows may exhibit markedly different observability characteristics depending on the combination of model backend, transport mechanism, and orchestration framework.

A key source of this discrepancy is that, unlike generated text, token usage is not treated as a first-class execution artifact with a well-defined exposure contract, but rather as auxiliary metadata. Consequently, whether token usage is observable depends jointly on (i) the underlying model API and its response schema, (ii) the transport layer through which inference results are delivered (e.g., streaming versus non-streaming), and (iii) the framework’s instrumentation and log-propagation strategy. In the absence of an agreed-upon contract, each layer independently decides how token usage is represented and whether it is forwarded, making end-to-end observability fragile and stack-dependent.

Backend- and modality-dependent loss of usage metadata.This lack of standardization manifests across both model backends and invocation modalities. For example, Gemini and Vertex AI do expose token usage information, but under response layouts and terminology that differ from OpenAI- or Anthropic-style APIs. Token usage may be reported through backend-specific metadata fields (e.g., reporting generation-side token usage as _candidate tokens_, rather than OpenAI-style output or completion tokens (langchain\_vertexai\_chatvertexai)), requiring backend-aware parsing logic to recover usage information. Beyond generation APIs, we further observe that usage metadata may be dropped entirely at the framework level for non-generative calls. In LangGraph, embedding model invocations (e.g., OpenAIEmbeddings and VertexAIEmbeddings) do not propagate token usage information, even when the underlying provider APIs support usage accounting. In such cases, the framework consumes partial response metadata internally without forwarding it to application-level telemetry or accounting hooks. As a consequence, orchestration frameworks such as LangGraph and MCP-Agent – many of which implicitly assume a synchronous, OpenAI-style usage schema – may fail to capture token usage across a range of execution paths unless explicit, backend- and modality-aware instrumentation is implemented. Importantly, these limitations do not arise from agent logic or missing backend signals, but from the absence of a stable, cross-provider observability contract that defines how usage metadata should be structured, preserved, and forwarded across abstraction boundaries.

Implications for MAS benchmarking.This inconsistency introduces blind spots in cost and efficiency analysis, particularly in heterogeneous multi-agent settings where different LLM backends coexist. It further demonstrates that observability properties cannot be assumed to be model-agnostic, motivating the need for standardized observability contracts that explicitly define which execution signals must be exposed by LLM APIs and agent frameworks.