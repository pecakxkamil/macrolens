import type { PreparedReading } from "./readingComparisons";
import type { PreparedFedTarget } from "./fedTarget";
import { EconomicExplanationTooltip } from "./EconomicExplanationTooltip";
import { economicExplanation, fedExplanation } from "./economicExplanations";

type Props = { reading: PreparedReading; target?: never } | { target: PreparedFedTarget; reading?: never };
export default function ReadingExplanation(props: Props) {
  const label = props.reading ? `${props.reading.label}: Economic meaning` : "Fed target range: Economic meaning";
  const explanation = props.reading ? economicExplanation(props.reading) : fedExplanation(props.target!);
  return <EconomicExplanationTooltip label={label} explanation={explanation} />;
}
