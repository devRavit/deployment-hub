# deployment-hub

개인 프로젝트들의 CD(Continuous Deployment) 중앙 관리 허브

## Overview

각 프로젝트의 CI는 해당 프로젝트에서 수행하고, CD는 이 저장소에서 중앙 관리합니다.
배포 타입별로 별도 워크플로(`apprunner.yml` / `lightsail.yml` / `curseforge.yml`)가 존재하며,
소스 리포에서 `repository_dispatch` 이벤트를 보내면 해당 워크플로가 트리거됩니다.

```
[프로젝트 repo]                       [deployment-hub]
    │                                       │
    ├─ CI (build, test)                     │
    ├─ Docker / Addon 패키지 빌드             │
    └─ repository_dispatch ──────────────>  ├─ projects/{project}.yml 로드
                                            ├─ Secrets Manager 에서 secret 해결
                                            ├─ 배포 타입별 워크플로 실행
                                            │   (App Runner / Lightsail / CurseForge)
                                            └─ GitHub Release 생성
```

## Project Configuration

`projects/{project}.yml` 형식으로 각 프로젝트 설정을 관리합니다. 공통 필드:

```yaml
name: <project>            # 프로젝트 식별자 (workflow 에서 그대로 사용)
type: apprunner            # apprunner | lightsail | curseforge
region: <aws-region>       # AWS 리전 (curseforge 제외)

aws:
  secrets_manager_id: production/<project>   # Secrets Manager secret ID
  ecr_role: <ecr-pull-role-name>             # ECR pull role (apprunner)
  instance_role: <runtime-instance-role-name>  # 런타임 IAM role (apprunner)
```

`AWS_ACCOUNT_ID` GitHub Secret 만 사용하고, role ARN 은 위 필드 + account ID 로 동적 조합됩니다.

### apprunner 설정 예시

```yaml
name: <project>
type: apprunner
region: <aws-region>

aws:
  ecr_role: <ecr-pull-role-name>
  instance_role: <runtime-instance-role-name>
  secrets_manager_id: production/<project>

apprunner:
  service_name: <service>
  port: <app-port>
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
    SPRING_PROFILES_ACTIVE: production
```

### lightsail 설정 예시

```yaml
name: <project>
type: lightsail
region: <aws-region>

aws:
  secrets_manager_id: production/<project>

lightsail:
  instance_name: <instance>
  container_name: <container>
  host_port: <host-port>           # Lightsail firewall 노출 포트
  container_port: <container-port> # 컨테이너 내부 listen 포트
  health_check:
    path: /health
    interval: 10
    timeout: 5
    retries: 3
  env:
    SPRING_PROFILES_ACTIVE: production
    JAVA_TOOL_OPTIONS: "-Xmx1024m -XX:+UseG1GC"
```

### curseforge 설정 예시

```yaml
name: <project>
source_repo: <github-owner>/<repo>
type: curseforge

curseforge:
  project_id: <curseforge-project-id>
  url: https://www.curseforge.com/wow/addons/<addon-slug>
```

## Secrets Management

AWS Secrets Manager 에서 `aws.secrets_manager_id` 컨벤션(`production/{project}`)으로 자동 탐색합니다.

- Secret ID 컨벤션: `production/<project>`
- Key format: `spring.mongodb.uri` (Spring property 형식)
- 자동 변환: `spring.mongodb.uri` → `SPRING_MONGODB_URI`

새 secret 추가 시 코드 변경 없이 Secrets Manager 에만 추가하면 자동 주입됩니다.

### 필수 GitHub Secrets

| Secret | 용도 | 사용 워크플로 |
|--------|------|--------------|
| `AWS_ACCOUNT_ID` | AWS 계정 ID (role ARN 조합) | apprunner / lightsail |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | AWS API 호출 | apprunner / lightsail |
| `LIGHTSAIL_SSH_KEY` | 인스턴스 키페어 private key 전문 | lightsail |
| `CF_API_KEY` | CurseForge Upload API 키 | curseforge |
| `PAT` | cross-repo 인증 (Release 생성 / dispatch) | 공통 |

## Supported Deployment Types

- **apprunner**: AWS App Runner (ECR 이미지 기반)
  - ⚠️ 2026-04-30 부로 AWS 가 신규 가입 중단 (deprecated). 기존 서비스는 유지·보안 패치만.
- **lightsail**: AWS Lightsail Instance (ECR 이미지 기반, SSH + `docker pull`/`restart` 방식)
  - 워커형 워크로드(자율 워커·고정 IP 필요·HTTP 진입 적음)에 적합
  - 인스턴스 측 사전 셋업: docker, AWS CLI, ECR pull 권한을 가진 IAM access key (`~/.aws/credentials`)
  - 포트 매핑: `host_port` ↔ `container_port`. 둘 생략 시 `port` 사용 (이전 호환)
  - 헬스체크: 인스턴스 localhost 의 `host_port` 로 curl 폴링
- **curseforge**: WoW Addon CurseForge 자동 배포 (BigWigs Packager 기반)
  - `repository_dispatch`(태그 push 시 자동) 또는 `workflow_dispatch`(수동 dry-run) 트리거
  - dry-run 모드: 패키지 zip 을 GitHub Actions artifact 로 출력 (CurseForge 등록 신청용)

## Rollback (Lightsail)

긴급 시 직전(또는 지정) 버전으로 1-step 복귀:

- GitHub Actions → **Rollback Lightsail** → Run workflow
- 입력: `project` (예: `miner`), `target_version` (비우면 ECR 직전 = latest-1 자동)
- 동작: ECR `:target` pull → 컨테이너 stop/rm/run → health check → 실패 시 `:latest` 자동 원복
- 직전 버전이 ECR 에 없으면 조용히 skip — 보관 범위는 `projects/<name>.yml` 의 `ecr.lifecycle.keep_count` 에 의존 (기본 배포는 latest + 직전 2개만 보관)

## Recent Changes

최신 변경 사항은 [docs/CHANGELOG.md](docs/CHANGELOG.md) 참조. 아래 영역은 `docs/CHANGELOG.md` push 시 자동 갱신됩니다.

<!-- CHANGELOG_START -->

## v0.1.0
`2026.05.02 (KST)`

CurseForge 배포 타입 추가 (WoW 애드온 지원)

- `.github/workflows/curseforge.yml`: BigWigs Packager 기반 CurseForge 자동 업로드
  - `repository_dispatch` (소스 리포 태그 push 트리거) + `workflow_dispatch` (수동 dry-run) 양쪽 지원
  - dry-run 모드: zip 산출물을 GitHub Actions artifact로 출력
- `projects/<addon>.yml`: 첫 WoW 애드온 프로젝트 추가 (project_id placeholder)
- README: Supported Deployment Types에 curseforge 추가
- 신규 시크릿: `CF_API_KEY` (CurseForge Upload API). cross-repo 인증은 기존 `PAT` 재사용 (스코프에 신규 애드온 repo 추가 필요)
- `projects/<addon>.yml`: CurseForge 승인 후 실제 project_id 적용

## v0.0.3
`2025.11.30 12:00`

프로젝트별 region 및 IAM role 설정 지원

- `projects.yml`에 `region`, `aws.ecr_role`, `aws.instance_role` 필드 추가
- GitHub Secrets에서 `AWS_ACCOUNT_ID`만 사용, role ARN은 동적 조합
- 배포 단순화: `start-deployment`만 호출 (마이그레이션 로직 제거)
- 불필요한 secrets 정리: `AWS_REGION`, `APP_RUNNER_*_ROLE_ARN` 삭제

## v0.0.2
`2025.11.29 22:22`

Secrets Manager 동적 주입 리팩토링

- `production/{project}` 컨벤션으로 자동 secret 탐색
- `spring.mongodb.uri` → `SPRING_MONGODB_URI` 자동 변환
- 프로젝트 설정 파일에서 secrets 항목 제거 (코드 변경 없이 secret 추가 가능)

<!-- CHANGELOG_END -->

## License

Private repository
