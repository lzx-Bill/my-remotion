import { HelloWorldCompositions } from "./compositions/cases/hello-world/register";
import { GitHubTrendingCompositions } from "./compositions/cases/github-trending/register";
import { NovelZhongKuiCompositions } from "./compositions/cases/novel-zhongkui/register";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <HelloWorldCompositions />
      <GitHubTrendingCompositions />
      <NovelZhongKuiCompositions />
    </>
  );
};