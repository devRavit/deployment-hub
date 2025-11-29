# deployment-hub

개인 프로젝트들의 CD(Continuous Deployment) 중앙 관리 허브

## Overview

각 프로젝트의 CI는 해당 프로젝트에서 수행하고, CD는 이 저장소에서 중앙 관리합니다.

```
[프로젝트 repo]          [deployment-hub]
    │                         │
    ├─ CI (build, test)       │
    ├─ Docker build & push    │
    └─ repository_dispatch ──>├─ Load project config
                              ├─ Resolve secrets
                              ├─ Deploy to App Runner
                              └─ Create GitHub Release
```

## Project Configuration

`projects/{project}.yml` 형식으로 각 프로젝트 설정 관리:

```yaml
name: stash
source_repo: devRavit/stash
type: apprunner

apprunner:
  service_name: stash
  port: 9090
  cpu: "0.25 vCPU"
  memory: "0.5 GB"
  health_check:
    path: /health
    interval: 10
    timeout: 5
    healthy_threshold: 1
    unhealthy_threshold: 5
  env:
    JAVA_TOOL_OPTIONS: "-Xmx256m -XX:+UseG1GC"
```

## Secrets Management

AWS Secrets Manager에서 `production/{project}` 컨벤션으로 자동 탐색:

- Secret ID: `production/stash`
- Key format: `spring.mongodb.uri` (Spring property 형식)
- 자동 변환: `spring.mongodb.uri` → `SPRING_MONGODB_URI`

새 secret 추가 시 코드 변경 없이 Secrets Manager에만 추가하면 자동 주입됩니다.

## Supported Deployment Types

- **apprunner**: AWS App Runner (ECR 이미지 기반)

## Recent Changes

<!-- CHANGELOG_START -->
<!-- CHANGELOG_END -->

## License

Private repository
