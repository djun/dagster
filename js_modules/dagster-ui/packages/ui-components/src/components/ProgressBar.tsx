// eslint-disable-next-line no-restricted-imports
import {ProgressBar as BlueprintProgressBar, ProgressBarProps} from '@blueprintjs/core';
import * as React from 'react';
import styled from 'styled-components';

import {Colors} from './Colors';

export const ProgressBar: React.FC<ProgressBarProps & {fillColor?: string}> = ({
  fillColor = Colors.Gray600,
  ...rest
}) => {
  return (
    <StyledProgressBar
      {...rest}
      intent="none"
      $fillColor={fillColor}
      stripes={rest.animate ? true : false}
    />
  );
};

const StyledProgressBar = styled(BlueprintProgressBar)<{$fillColor: string}>`
  &.bp4-progress-bar {
    background: transparent;

    ::before {
      content: '';
      background: ${(p) => p.$fillColor};
      position: absolute;
      inset: 0;
      opacity: 0.25;
    }

    .bp4-progress-meter {
      background-color: ${(p) => p.$fillColor};
    }
  }
`;
